select id from {{ ref('plate_defects') }} where TypeOfSteel_A300 + TypeOfSteel_A400 <> 1
