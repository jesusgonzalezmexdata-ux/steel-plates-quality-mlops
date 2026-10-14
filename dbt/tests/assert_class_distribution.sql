with observed as (
    select defect_class, count(*) as observed_count
    from {{ ref('plate_defects') }} group by defect_class
)
select *
from observed
full outer join {{ ref('expected_class_counts') }} using (defect_class)
where observed_count is distinct from expected_count
