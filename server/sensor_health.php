<?php
declare(strict_types=1);

// Use original sensor values: cleaned data can contain an older imputed value.
function sensor_health(array $raw): array {
    $check = static function (string $field, float $low, float $high) use ($raw): array {
        $value = $raw[$field] ?? null;
        if ($value === null || $value === '') return ['state'=>'MISSING', 'value'=>null];
        if (is_bool($value) || !is_numeric($value) || !is_finite((float)$value)
            || (float)$value < $low || (float)$value > $high) {
            return ['state'=>'INVALID', 'value'=>null];
        }
        return ['state'=>'REPORTING', 'value'=>(float)$value];
    };
    $health = [];
    foreach ([1, 2] as $probe) {
        $result = $check("soil_moisture_{$probe}_adc", 0, 4095);
        if ($result['state'] === 'REPORTING') {
            $adc = $result['value'];
            $result['state'] = ($adc <= 5 || $adc >= 4090 || floor($adc) !== $adc) ? 'INVALID' : 'REPORTING';
            // An analog value alone cannot prove that the probe is connected.
            $result['response_verified'] = false;
        }
        $health["soil_probe_{$probe}"] = $result;
    }
    $health['soil_temperature'] = $check('soil_temperature_c', -20, 70);
    $temperature = $check('air_temperature_c', -15, 60);
    $humidity = $check('relative_humidity_pct', 0, 100);
    $health['air_temperature_humidity'] = [
        'state'=>in_array('INVALID', [$temperature['state'], $humidity['state']], true) ? 'INVALID'
            : (($temperature['state'] === 'MISSING' || $humidity['state'] === 'MISSING') ? 'MISSING' : 'REPORTING'),
        'temperature'=>$temperature['value'], 'humidity'=>$humidity['value'],
    ];
    $health['light'] = $check('light_lux', 0, 120000);
    return $health;
}

// Temporary calibration is an estimate calculated when reading data, not a
// measured/calibrated value written into the cleaned observation contract.
function provisional_moisture(array $raw, array $endpoints): array {
    $result=[]; $indices=[];
    foreach ([1,2] as $probe) {
        $index=null; $adc=$raw["soil_moisture_{$probe}_adc"]??null;
        [$dry,$wet]=$endpoints[$probe]??[null,null];
        if (is_int($adc) && $adc>5 && $adc<4090 && is_numeric($dry) && is_numeric($wet)
            && is_finite((float)$dry) && is_finite((float)$wet)
            && $dry>=0 && $dry<=4095 && $wet>=0 && $wet<=4095 && abs($dry-$wet)>=100) {
            $index=round(max(0,min(100,100*($adc-$dry)/($wet-$dry))),2);
            $indices[]=$index;
        }
        $result["estimated_soil_moisture_{$probe}_index"]=$index;
    }
    $result['estimated_moisture_avg_index']=$indices?round(array_sum($indices)/count($indices),2):null;
    return $result;
}
