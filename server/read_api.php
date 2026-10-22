<?php
declare(strict_types=1);

function require_read_api_key(): void {
    $path=getenv('NAI_MIRIS_READ_KEYS')?:__DIR__.'/read_api_keys.php';
    if (!is_file($path)) reply(['error'=>'Read API key is not configured'],503);
    $hashes=require $path;
    $key=$_SERVER['HTTP_X_API_KEY']??'';
    if (!is_string($key) || !preg_match('/^[A-Za-z0-9_-]{32,128}$/D',$key)) {
        reply(['error'=>'A valid X-API-Key header is required'],401);
    }
    $hash=hash('sha256',$key);
    foreach (is_array($hashes)?$hashes:[] as $expected) {
        if (is_string($expected) && strlen($expected)===64 && hash_equals($expected,$hash)) return;
    }
    reply(['error'=>'Invalid read API key'],401);
}

function realtime_readings(?string $node): array {
    global $config;
    $data=[];
    $now=time();
    $zones=['NODE_01'=>'ZONE_A','NODE_02'=>'ZONE_B'];
    foreach ($node?[$node]:array_keys($zones) as $id) {
        $records=rows($id,1);
        $r=$records[0]??null;
        $age=$r?$now-stamp($r['timestamp'])->getTimestamp():null;
        $data[]=[
            'node_id'=>$id,'zone_id'=>$zones[$id],'available'=>$r!==null,
            'record_id'=>$r['record_id']??null,'sample_time_utc'=>$r['timestamp']??null,
            'received_utc'=>$r['received_utc']??null,'age_seconds'=>$age,
            'stale'=>$age===null || $age>420 || $age< -600,
            'timestamp_source'=>$r?(str_contains($r['quality_flags']??'','timestamp_fallback')?'server_received':'device'):null,
            'readings'=>$r['raw_measurements']??null,
            'calibrated_moisture_index'=>$r['soil_moisture_avg_index']??null,
            'estimated_moisture_index'=>($r['soil_moisture_avg_index']??null)===null?($r['estimated_moisture_avg_index']??null):null,
            'moisture_calibration_status'=>($r['soil_moisture_avg_index']??null)!==null?'calibrated'
                :(($r['estimated_moisture_avg_index']??null)!==null?'provisional':'unconfigured'),
            'sensor_health'=>$r['sensor_health']??null,
            'quality'=>$r?['status'=>$r['record_status'],'flags'=>$r['quality_flags'],'imputed_fields'=>$r['imputed_fields']]:null,
        ];
    }
    return ['schema_version'=>'1.0.0','server_time_utc'=>gmdate('Y-m-d\TH:i:s\Z',$now),
        'sample_interval_seconds'=>max(1,(int)($config['sample_minutes']??5))*60,
        'stale_after_seconds'=>420,'count'=>count($data),'data'=>$data];
}
