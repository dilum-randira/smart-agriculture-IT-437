<?php
declare(strict_types=1);
require_once __DIR__.'/sensor_health.php';
date_default_timezone_set('UTC');
ini_set('display_errors', '0');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
header('Referrer-Policy: same-origin');
header("Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'");
function reply(array $data, int $code=200): never {
    http_response_code($code); header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_THROW_ON_ERROR); exit;
}
$configPath=getenv('NAI_MIRIS_CONFIG')?:__DIR__.'/config.php';
if (!is_file($configPath)) reply(['error'=>'Hosting configuration is not installed'],503);
$config = require $configPath;
$secure = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') || (int)($_SERVER['SERVER_PORT']??0) === 443;
$local = ($config['allow_http_local']??false) && in_array($_SERVER['REMOTE_ADDR']??'', ['127.0.0.1','::1'],true);
if (!$secure && !$local) reply(['error'=>'HTTPS is required'],426);
function db(): PDO {
    static $pdo; global $config;
    if (!$pdo) {
        $d=$config['db'];
        $pdo=new PDO('mysql:host='.$d['host'].';port='.(int)$d['port'].';dbname='.$d['name'].';charset=utf8mb4',
            $d['user'],$d['password'],[PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION, PDO::ATTR_EMULATE_PREPARES=>false]);
        $pdo->exec("SET time_zone = '+00:00'");
    }
    return $pdo;
}
function query(string $sql, array $args=[]): PDOStatement {
    $q=db()->prepare($sql); $q->execute($args); return $q;
}
function start_session(): void {
    global $secure;
    if (session_status()===PHP_SESSION_ACTIVE) return;
    ini_set('session.use_strict_mode','1'); ini_set('session.use_only_cookies','1');
    session_name('naimiris_session');
    session_set_cookie_params(['lifetime'=>0,'path'=>'/','secure'=>$secure,'httponly'=>true,'samesite'=>'Strict']);
    session_start();
    if (isset($_SESSION['login_time']) && time()-$_SESSION['login_time']>43200) $_SESSION=[];
    $_SESSION['csrf'] ??= bin2hex(random_bytes(32));
}
function authenticated(): bool { start_session(); return !empty($_SESSION['authenticated']); }
function require_login(): void { if (!authenticated()) reply(['error'=>'Login required'],401); }
function require_csrf(): void {
    start_session();
    if (!hash_equals($_SESSION['csrf'], $_SERVER['HTTP_X_CSRF_TOKEN']??'')) reply(['error'=>'Invalid request token'],403);
}
function device_node(): string {
    global $config;
    $auth=$_SERVER['HTTP_AUTHORIZATION']??$_SERVER['REDIRECT_HTTP_AUTHORIZATION']??'';
    if (!preg_match('/^Bearer ([A-Za-z0-9_-]{32,128})$/D',$auth,$m)) reply(['error'=>'Device authentication required'],401);
    $hash=hash('sha256',$m[1]);
    foreach ($config['device_token_hashes'] as $node=>$expected) {
        if (is_string($expected) && strlen($expected)===64 && hash_equals($expected,$hash)) return $node;
    }
    reply(['error'=>'Invalid device key'],401);
}
function body(): array {
    if (stripos($_SERVER['CONTENT_TYPE']??'','application/json')!==0) reply(['error'=>'Use application/json'],415);
    $text=file_get_contents('php://input',false,null,0,8193);
    if (strlen($text)>8192) reply(['error'=>'Payload exceeds 8192 bytes'],413);
    try { $value=json_decode($text,true,32,JSON_THROW_ON_ERROR); }
    catch (JsonException $e) { reply(['error'=>'Invalid JSON'],400); }
    if (!is_array($value) || !str_starts_with(ltrim($text),'{')) reply(['error'=>'JSON object required'],400);
    return $value;
}
function iso(DateTimeInterface $d): string { return $d->format('Y-m-d\TH:i:s\Z'); }
function stamp(string $s): DateTimeImmutable {
    if (!preg_match('/^\d{4}-\d{2}-\d{2}T.*(Z|[+-]\d{2}:\d{2})$/D',$s)) throw new InvalidArgumentException('Timestamp must include timezone');
    $d=new DateTimeImmutable($s); $errors=DateTimeImmutable::getLastErrors();
    if ($errors && ($errors['warning_count'] || $errors['error_count'])) throw new InvalidArgumentException('Invalid timestamp');
    return $d->setTimezone(new DateTimeZone('UTC'));
}
function rows(?string $node=null, int $limit=500, bool $raw=false): array {
    global $config;
    $where=$node ? ' WHERE node_id=?' : '';
    $records=query('SELECT * FROM observations'.$where.' ORDER BY timestamp_utc DESC, id DESC LIMIT '.max(1,min(10000,$limit)), $node?[$node]:[])->fetchAll(PDO::FETCH_ASSOC);
    $data=[];
    foreach (array_reverse($records) as $r) {
        $original=json_decode($r['raw_json'],true,32,JSON_THROW_ON_ERROR);
        if ($raw) { $data[]=$original; continue; }
        $clean=json_decode($r['cleaned_json'],true,32,JSON_THROW_ON_ERROR);
        $clean['sensor_health']=sensor_health($original);
        $clean=array_merge($clean,provisional_moisture($original,$config['provisional_calibration'][$r['node_id']]??[]));
        $measurementFields=['soil_moisture_1_adc','soil_moisture_2_adc','soil_moisture_1_mv','soil_moisture_2_mv',
            'soil_temperature_c','air_temperature_c','relative_humidity_pct','light_lux','wifi_rssi_dbm'];
        $clean['raw_measurements']=array_replace(array_fill_keys($measurementFields,null),array_intersect_key($original,array_flip($measurementFields)));
        foreach (['soil_moisture_1_adc','soil_moisture_2_adc','soil_moisture_1_mv','soil_moisture_2_mv','wifi_rssi_dbm','sequence_number','boot_id','firmware_version','reset_reason'] as $k) $clean[$k]=$original[$k]??null;
        $clean['received_utc']=iso(new DateTimeImmutable($r['received_utc'],new DateTimeZone('UTC')));
        $data[]=$clean;
    }
    return $data;
}
