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
start_session();
header('Content-Type: text/html; charset=utf-8');
$page=file_get_contents($privateDir.'/dashboard.html');
$displayKey='';
$displayPath=getenv('NAI_MIRIS_READ_DISPLAY')?:$privateDir.'/read_api_display.php';
$hashPath=getenv('NAI_MIRIS_READ_KEYS')?:$privateDir.'/read_api_keys.php';
if (is_file($displayPath) && is_file($hashPath)) {
    $candidate=require $displayPath;
    $hashes=require $hashPath;
    if (is_string($candidate) && preg_match('/^[A-Za-z0-9_-]{32,128}$/D',$candidate) && is_array($hashes)) {
        foreach ($hashes as $hash) {
            if (is_string($hash) && hash_equals($hash,hash('sha256',$candidate))) { $displayKey=$candidate; break; }
        }
    }
}
$page=str_replace('__READ_API_KEY__',htmlspecialchars($displayKey,ENT_QUOTES,'UTF-8'),$page);
if (!empty($config['allow_http_local'])) $page=str_replace('<body>','<body><div style="padding:10px;background:#64491c;color:#fff;text-align:center">LOCAL TEST PREVIEW — generated test readings, not field measurements</div>',$page);
echo str_replace('__CSRF_TOKEN__',htmlspecialchars($_SESSION['csrf'],ENT_QUOTES,'UTF-8'),$page);
