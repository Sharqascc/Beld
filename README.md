# Beld

Beld is a floor-plan generation repository.

## Files

- `beld/v51_optimizer.py` - earlier optimizer
- `beld/v52_optimizer.py` - optimizer with opening placement for doors and windows

## Run

```bash
python beld/v52_optimizer.py
```

## Notes

`v52_optimizer.py` extracts wall segments from room polygons, classifies interior/exterior walls, places doors on interior shared walls, places windows on exterior walls, and exports an SVG preview.
