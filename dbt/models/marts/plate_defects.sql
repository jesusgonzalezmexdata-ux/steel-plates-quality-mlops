-- One row per plate with its single defect class derived from the one-hot target.
select
    *,
    Pastry + Z_Scratch + K_Scatch + Stains + Dirtiness + Bumps + Other_Faults as target_sum,
    case
        when Pastry = 1 then 'Pastry'
        when Z_Scratch = 1 then 'Z_Scratch'
        when K_Scatch = 1 then 'K_Scatch'
        when Stains = 1 then 'Stains'
        when Dirtiness = 1 then 'Dirtiness'
        when Bumps = 1 then 'Bumps'
        when Other_Faults = 1 then 'Other_Faults'
    end as defect_class
from {{ ref('stg_steel_plates') }}
