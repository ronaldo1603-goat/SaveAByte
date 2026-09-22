# SaveAByte

AI-powered food-waste tracking for school cafeterias. A camera at the tray-return station photographs finished trays, and a Vision Language Model estimates how much food is left in each compartment. A tap counter at the serving station records extra-portion requests. Both data streams feed a per-dish dashboard that tells the kitchen what to cook less of, and what to cook more of.

Built by **Team Bông** for the NEXUS High School Innovation Challenge 2026 (N-HSIC 2026).

## The problem

School kitchens cook the same portions week after week with no feedback on what students actually eat. Most food-waste solutions act *after* the waste happens (donation, composting, bulk weighing). SaveAByte closes the feedback loop by measuring waste **per dish, per tray**, so portions can be adjusted before food is wasted.

## How it works

1. **Scan**: a tray photo (before or after the meal) goes to Gemini Flash, which returns structured JSON per compartment: `dish_name`, `has_food`, `fill_fraction` (0.0 = eaten clean, 1.0 = untouched).
2. **Count**: serving staff tap once for each extra-portion request.
3. **Decide**: the dashboard merges both streams. High waste means reduce the portion. Many taps with low waste means increase it.

## Project structure

```
saveabyte/
├── app.py                  
├── pages/
│   ├── 2_Tap_Counter.py    
│   ├── 3_Dashboard.py      
│   └── 4_Calibration.py    
├── src/
│   └── nexus/
│       ├── gemini.py       
│       ├── models.py       
│       ├── db.py           
│       ├── dashboard.py    
│       └── style.py        
├── phase2.py               
├── pyproject.toml
├── uv.lock
└── .gitignore      
```

## Limitations & next steps

- The Gemini free-tier quota limits daily scans, so real deployment needs a paid tier.
- Recommendation thresholds (0.30 / 0.15) are not yet calibrated on real cafeteria data.
- The menu is hard-coded; per-compartment menu-mapping is planned.
- Phase 2 plans: calibration against ~100 physically weighed trays, a custom YOLO model trained on VLM pseudo-labels, and demand forecasting.

## Built with

Streamlit · Supabase · Google Gemini Flash · Pydantic v2 · pandas · uv

## Team

Team Bông: Ngô Tuấn Minh, Nguyễn Minh Điền Sunny, Phạm Ngọc Thanh