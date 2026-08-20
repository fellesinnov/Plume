# CORMIX profile comparison

For each test case you want to compare, create a CSV here named:

`<case_id>.csv`

Example:

`T01_baseline.csv`

Required columns:

```text
x_m,z_m,dilution_centerline
```

Optional:

```text
y_m
```

The tool computes horizontal distance as `sqrt(x^2+y^2)` and interpolates its own trajectory/dilution at
the CORMIX distances.

Use the actual CORMIX/CorJet centerline dilution, not bulk dilution, when available.

`PROFILE_TEMPLATE.csv` is only a formatting example; its values are fictitious and must not be used for
calibration.
