<?php
declare(strict_types=1);
if (PHP_VERSION_ID < 80200) {
    http_response_code(503);
    exit('Please select PHP 8.2 or newer for this domain in cPanel.');
}
$privateDir=__DIR__;
if (!is_file(__DIR__.'/bootstrap.php') || !is_file(__DIR__.'/config.php')) {
    http_response_code(503);
    exit('Upload all files from the root upload ZIP into the same directory.');
}
require $privateDir.'/bootstrap.php';
require $privateDir.'/processing.php';
try {
    $route=$_GET['route']??''; $method=$_SERVER['REQUEST_METHOD'];
    if ($route==='c1/realtime') {
        if ($method!=='GET') reply(['error'=>'GET required'],405);
        require_once $privateDir.'/read_api.php';
        require_read_api_key();
        $node=$_GET['node_id']??null;
        if ($node!==null && (!is_string($node) || !in_array($node,['NODE_01','NODE_02'],true))) {
            reply(['error'=>'Unknown node'],400);
        }
        reply(realtime_readings($node));
    }
    if ($route==='ingest') {
        if ($method!=='POST') reply(['error'=>'POST required'],405);
        $node=device_node(); $raw=body();
        if (($raw['node_id']??null)!==$node) reply(['error'=>'Device key belongs to another node'],403);
        reply(save_reading($raw));
    }
    // Dashboard data is public; ingestion still requires a device key.
    $node=$_GET['node_id']??null;
    if ($node!==null&&!in_array($node,['NODE_01','NODE_02'],true)) reply(['error'=>'Unknown node'],400);
    if (isset($_GET['origin'])&&$_GET['origin']!=='real') reply(['error'=>'Only real readings are available'],400);
    $limit=filter_var($_GET['limit']??(str_starts_with($route,'exports/')?10000:500),FILTER_VALIDATE_INT);
    if ($limit===false||$limit<1||$limit>10000) reply(['error'=>'Invalid limit'],400);
    if ($route==='c3/manual-watering') {
        if ($method==='POST') {
            require_csrf(); $r=body(); $time=stamp($r['timestamp']??''); $zone=$r['zone_id']??'';
            $liters=finite_value($r['water_applied_liters']??null,0.01,1000); $notes=$r['notes']??'';
            if (!in_array($zone,['ZONE_A','ZONE_B'],true)||$liters===null||!is_string($notes)||mb_strlen($notes)>500) reply(['error'=>'Invalid watering record'],400);
            query('INSERT INTO manual_watering(timestamp_utc,zone_id,water_applied_liters,notes) VALUES(?,?,?,?)',[$time->format('Y-m-d H:i:s'),$zone,$liters,$notes]);
            reply(['id'=>(int)db()->lastInsertId(),'timestamp'=>iso($time),'data_origin'=>'real'],201);
        }
    } elseif ($method!=='GET') reply(['error'=>'GET required'],405);
    if ($route==='c3/manual-watering'||$route==='exports/manual-watering.csv') {
        $data=query('SELECT * FROM manual_watering ORDER BY timestamp_utc DESC LIMIT '.$limit)->fetchAll(PDO::FETCH_ASSOC);
        foreach ($data as &$r) { $r['timestamp']=iso(new DateTimeImmutable($r['timestamp_utc'])); unset($r['timestamp_utc']); $r['water_applied_liters']=(float)$r['water_applied_liters']; $r['data_origin']='real'; } unset($r);
        if ($route==='c3/manual-watering') reply(['data'=>$data]);
        output_csv($data,['id','timestamp','zone_id','water_applied_liters','notes','data_origin'],'manual-watering');
    }
    $latest=[]; foreach (['NODE_01','NODE_02'] as $n) { $r=rows($n,1); if ($r) $latest[]=$r[0]; }
    $total=(int)query('SELECT COUNT(*) FROM observations')->fetchColumn();
    if ($route==='c1/live-status') reply(['api_running'=>true,'transport'=>'https','storage'=>'mysql',
        'server_time_utc'=>gmdate('Y-m-d\TH:i:s\Z'),'total_real_records'=>$total,'last_measurements'=>$latest]);
    if ($route==='health') reply(['ok'=>true,'transport'=>'https','storage'=>'mysql','data_records'=>['real'=>$total]]);
    if ($route==='c1/latest') reply(['schema_version'=>'1.0.0','data'=>$latest]);
    if ($route==='c1/contract') { header('Content-Type: application/json'); readfile($privateDir.'/contract.json'); exit; }
    if ($route==='c1/raw') reply(['count_limit'=>$limit,'data'=>array_reverse(rows($node,$limit,true))]);
    if ($route==='c1/node-health') {
        $data=[]; foreach (['NODE_01'=>'ZONE_A','NODE_02'=>'ZONE_B'] as $n=>$z) {
            $match=array_values(array_filter($latest,fn($r)=>$r['node_id']===$n)); $r=$match[0]??null;
            $age=$r?(time()-stamp($r['timestamp'])->getTimestamp())/60:null;
            $data[]=['node_id'=>$n,'zone_id'=>$z,'last_record_timestamp'=>$r['timestamp']??null,'minutes_since_sample'=>$age,'recent_sample'=>$age!==null&&$age>=0&&$age<=7];
        } reply(['data'=>$data]);
    }
    $data=rows($node,$limit);
    if ($route==='c1/observations') {
        $start=isset($_GET['start'])?stamp($_GET['start']):null; $end=isset($_GET['end'])?stamp($_GET['end']):null;
        $data=array_values(array_filter($data,fn($r)=>(!$start||stamp($r['timestamp'])>=$start)&&(!$end||stamp($r['timestamp'])<=$end)&&(!isset($_GET['zone_id'])||$r['zone_id']===$_GET['zone_id'])));
        // Cleaned contract contains exactly its 28 documented fields.
        $data=array_map(fn($r)=>array_intersect_key($r,array_flip(C1_FIELDS)),$data);
    }
    if (in_array($route,['c1/live-history','c1/observations'],true)) reply(['schema_version'=>'1.0.0','count'=>count($data),'data'=>$data]);
    if (preg_match('~^exports/(c2|c3|c4|all)\.csv$~D',$route,$m)) output_csv($data,C1_FIELDS,$m[1]);
    reply(['error'=>'Route not found'],404);
} catch (InvalidArgumentException|TypeError $e) { reply(['error'=>$e->getMessage()],400); }
catch (Throwable $e) { error_log('Nai Miris API: '.get_class($e).': '.$e->getMessage()); reply(['error'=>'Server unavailable; check hosting configuration and private error logs'],503); }
function output_csv(array $rows,array $fields,string $name): never {
    header('Content-Type: text/csv; charset=utf-8'); header('Content-Disposition: attachment; filename="nai_miris_'.$name.'.csv"');
    $out=fopen('php://output','w'); fputcsv($out,$fields,',','"','');
    foreach ($rows as $row) {
        $values=[]; foreach ($fields as $f) {
            $v=$row[$f]??'';
            if (is_bool($v)) $v=$v?'true':'false';
            // Prevent spreadsheet formulas in user-written watering notes.
            if (is_string($v)&&preg_match('/^[=+@\t\r]/',$v)) $v="'".$v;
            if ($f==='notes'&&is_string($v)&&str_starts_with($v,'-')) $v="'".$v;
            $values[]=$v;
        } fputcsv($out,$values,',','"','');
    } fclose($out); exit;
}
