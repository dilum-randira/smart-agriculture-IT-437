<?php
declare(strict_types=1);
const C1_FIELDS=['schema_version','record_id','timestamp','node_id','zone_id',
 'soil_moisture_1_index','soil_moisture_2_index','soil_moisture_avg_index',
 'soil_temperature_c','air_temperature_c','relative_humidity_pct','light_lux',
 'rain_detected','rain_source','rainfall_mm_24h','forecast_rain_mm_next_24h',
 'forecast_air_temp_max_c_next_24h','soil_moisture_change_1h_index',
 'air_temperature_avg_24h_c','vpd_kpa','quality_score','is_anomaly',
 'is_imputed','imputed_fields','quality_flags','record_status','weather_source','data_origin'];
function finite_value(mixed $v,float $low,float $high): ?float {
    if (is_bool($v)||$v===null||!is_numeric($v)) return null;
    $n=(float)$v; return is_finite($n)&&$n>=$low&&$n<=$high?$n:null;
}
function identity(array $raw): string {
    $node=$raw['node_id']??''; $zones=['NODE_01'=>'ZONE_A','NODE_02'=>'ZONE_B'];
    if (!is_string($node)||!isset($zones[$node])||($raw['zone_id']??null)!==$zones[$node]) throw new InvalidArgumentException('Invalid node/zone mapping');
    if (($raw['data_origin']??null)!=='real') throw new InvalidArgumentException('Only real sensor readings are accepted');
    $boot=$raw['boot_id']??null; $seq=$raw['sequence_number']??null;
    if (!is_string($boot)||!preg_match('/^[A-Za-z0-9_-]{1,90}$/D',$boot)) throw new InvalidArgumentException('Invalid boot_id');
    if (!is_int($seq)||$seq<1||$seq>1000000000) throw new InvalidArgumentException('Invalid sequence_number');
    return $node.'_'.$boot.'_'.$seq;
}
function process_record(array $raw,string $rid,DateTimeImmutable $received): array {
    global $config;
    $node=$raw['node_id']; $errors=[]; $imputed=[];
    try {
        $time=stamp($raw['timestamp']??'');
        if ($time>$received->modify('+10 minutes')||$time<$received->modify('-7 days')) throw new InvalidArgumentException('Unreliable sensor clock');
    } catch (Throwable $e) { $time=$received; $errors[]='timestamp_fallback_to_server_received_at'; }
    $sqlTime=$time->format('Y-m-d H:i:s');
    $previous=query('SELECT cleaned_json FROM observations WHERE node_id=? AND timestamp_utc<? AND timestamp_utc>=? ORDER BY timestamp_utc DESC,id DESC LIMIT 1',[$node,$sqlTime,$time->modify('-65 minutes')->format('Y-m-d H:i:s')])->fetchColumn();
    $prev=$previous?json_decode($previous,true):null;
    $r=array_fill_keys(C1_FIELDS,null);
    $r['schema_version']='1.0.0'; $r['record_id']=$rid; $r['timestamp']=iso($time);
    $r['node_id']=$node; $r['zone_id']=$raw['zone_id']; $r['data_origin']='real';
    foreach ([1,2] as $i) {
        $adc=finite_value($raw["soil_moisture_{$i}_adc"]??null,0,4095);
        if ($adc===null||$adc<=5||$adc>=4090) { $errors[]="soil_moisture_{$i}_adc_missing_or_rail"; continue; }
        [$dry,$wet]=$config['calibration'][$node][$i]??[null,null];
        $dry=finite_value($dry,0,4095); $wet=finite_value($wet,0,4095);
        if ($dry===null||$wet===null||abs($dry-$wet)<100) $errors[]="uncalibrated_soil_moisture_{$i}_index";
        else $r["soil_moisture_{$i}_index"]=round(max(0,min(100,100*($adc-$dry)/($wet-$dry))),2);
    }
    $indices=array_values(array_filter([$r['soil_moisture_1_index'],$r['soil_moisture_2_index']],fn($x)=>$x!==null));
    $r['soil_moisture_avg_index']=$indices?round(array_sum($indices)/count($indices),2):null;
    $specs=['soil_temperature_c'=>[-20,70,9],'air_temperature_c'=>[-15,60,9],
        'relative_humidity_pct'=>[0,100,32],'light_lux'=>[0,120000,120000]];
    foreach ($specs as $field=>[$low,$high,$jump]) {
        $value=finite_value($raw[$field]??null,$low,$high);
        if ($value===null) {
            $errors[]=$field.'_missing_or_invalid';
            if (($prev[$field]??null)!==null) { $value=$prev[$field]; $imputed[]=$field; }
        }
        if ($value!==null && ($prev[$field]??null)!==null && abs($value-$prev[$field])>$jump) $errors[]=$field.'_abrupt_change';
        $r[$field]=$value===null?null:round($value,2);
    }
    if (is_bool($raw['rain_detected']??null)) { $r['rain_detected']=$raw['rain_detected']; $r['rain_source']=$node; }
    if ($r['air_temperature_c']!==null&&$r['relative_humidity_pct']!==null) {
        $t=$r['air_temperature_c']; $r['vpd_kpa']=round(0.6108*exp(17.27*$t/($t+237.3))*(1-$r['relative_humidity_pct']/100),3);
    }
    $match=query('SELECT cleaned_json FROM observations WHERE node_id=? AND timestamp_utc BETWEEN ? AND ? ORDER BY ABS(TIMESTAMPDIFF(SECOND,timestamp_utc,?)) LIMIT 1',
        [$node,$time->modify('-70 minutes')->format('Y-m-d H:i:s'),$time->modify('-50 minutes')->format('Y-m-d H:i:s'),$time->modify('-60 minutes')->format('Y-m-d H:i:s')])->fetchColumn();
    if ($match) { $m=json_decode($match,true); if ($m['soil_moisture_avg_index']!==null&&$r['soil_moisture_avg_index']!==null) $r['soil_moisture_change_1h_index']=round($r['soil_moisture_avg_index']-$m['soil_moisture_avg_index'],2); }
    $history=query('SELECT timestamp_utc,cleaned_json FROM observations WHERE node_id=? AND timestamp_utc>=? AND timestamp_utc<? ORDER BY timestamp_utc',[$node,$time->modify('-24 hours')->format('Y-m-d H:i:s'),$sqlTime])->fetchAll(PDO::FETCH_ASSOC);
    $temps=[]; foreach ($history as $h) { $x=json_decode($h['cleaned_json'],true); if ($x['air_temperature_c']!==null) $temps[]=$x['air_temperature_c']; }
    if ($r['air_temperature_c']!==null) $temps[]=$r['air_temperature_c'];
    $required=(int)ceil(1440/max(1,(int)$config['sample_minutes'])*0.94);
    if (count($temps)>=$required && $history && new DateTimeImmutable($history[0]['timestamp_utc'])<=$time->modify('-23 hours')) $r['air_temperature_avg_24h_c']=round(array_sum($temps)/count($temps),2);
    $missing=0; foreach (['soil_moisture_1_index','soil_moisture_2_index',...array_keys($specs)] as $f) if ($r[$f]===null) $missing++;
    $faults=array_filter($errors,fn($s)=>!str_starts_with($s,'uncalibrated_'));
    $r['quality_score']=round(max(0,1-$missing*0.10-count($imputed)*0.05-count($faults)*0.06),2);
    $r['is_anomaly']=(bool)$faults; $r['is_imputed']=(bool)$imputed; $r['imputed_fields']=implode(';',$imputed);
    $errors=array_values(array_unique($errors)); sort($errors); $r['quality_flags']=implode(';',$errors);
    $r['record_status']=$missing>=4?'INVALID':($errors?'WARN':'OK');
    return $r;
}
function save_reading(array $raw): array {
    $rid=identity($raw); $pdo=db(); $pdo->beginTransaction();
    try {
        // Serialize same-node computations, including simultaneous/retried uploads.
        query('SELECT node_id FROM ingest_locks WHERE node_id=? FOR UPDATE',[$raw['node_id']]);
            $existing=query('SELECT record_id FROM observations WHERE record_id=?',[$rid])->fetchColumn();
            if ($existing) { $pdo->commit(); return ['ok'=>true,'record_id'=>$rid,'duplicate'=>true]; }
            $now=new DateTimeImmutable('now',new DateTimeZone('UTC')); $clean=process_record($raw,$rid,$now);
            query('INSERT INTO observations(record_id,node_id,zone_id,timestamp_utc,received_utc,raw_json,cleaned_json) VALUES(?,?,?,?,?,?,?)',
                [$rid,$raw['node_id'],$raw['zone_id'],stamp($clean['timestamp'])->format('Y-m-d H:i:s'),$now->format('Y-m-d H:i:s'),json_encode($raw,JSON_THROW_ON_ERROR),json_encode($clean,JSON_THROW_ON_ERROR)]);
            $pdo->commit(); return ['ok'=>true,'record_id'=>$rid,'duplicate'=>false];
    } catch (Throwable $e) { if ($pdo->inTransaction()) $pdo->rollBack(); throw $e; }
}
