select count(*) as rows from {{ ref('plate_defects') }} having count(*) <> 1941
