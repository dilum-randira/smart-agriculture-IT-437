# Practice 03 — Synthetic IoT → Prediction Contract

**සිංහලෙන්:** මේක C1 device එකෙන් සැබෑ data ගන්න system එකක් නෙවෙයි. IoT readings ආවොත් C2 system එක ක්‍රියා කරන විදිහ **synthetic example** එකකින් ඉගෙන ගන්න exercise එකක්.

## Workflow

1. \`schema.py\`: timestamps with timezone, required units and value ranges validate කරන්න.
2. \`replay.py\`: එක් පැයකට readings හතරක් (15-minute interval) synthetic source එකෙන් ලබා දෙන්න.
3. \`hourly.py\`: පැයක් සම්පූර්ණ නම් temperature/moisture/RH average කරන්න; rainfall sum කරන්න. Missing hours අතහරින්න.
4. \`forecast.py\`: plot-specific contiguous 48-hour history සහ freshness check කරන්න; insufficient/stale නම් safe status එකක් return කරන්න.
5. \`demo.py\`: අවසානයේ පැය 24කට **persistence reference** එකක් generate කරන්න. **මෙය trained LSTM/AI prediction එකක් නෙවෙයි.**

### Google Colab

Existing runtime හි repo folder එකට යන්න; latest feature branch pull කරන්න:

\`\`\`python
%cd /content/smart-agriculture-IT-437
!git switch feature/c2-ml-foundation
!git pull --ff-only
!python -m unittest discover -s c2/tests -v
!python c2/practice/iot_replay/demo.py
!python c2/practice/iot_replay/demo.py --mode missing
\`\`\`

New runtime නම් \`!git clone --branch feature/c2-ml-foundation https://github.com/dilum-randira/smart-agriculture-IT-437.git\` ඉස්සෙල්ලා run කරන්න.

Expected: \`valid\` demo එක \`provisional\` forecast එකක් දෙයි; \`missing\` demo එකේ history gap නිසා \`unavailable\` status එකක් ලැබෙයි. මේ status දෙකේ වෙනස Viva එකට හොඳ practice එකක්.

**Scope:** This toy adapter assumes a synthetic soil moisture *percentage*, not confirmed volumetric water content or calibrated real sensor measurements. Real C1 integration needs approved schema, calibration, quality flags, site data, growing stages, and independent Nai Miris harvest labels. No real-time collection or ML model training is claimed.
