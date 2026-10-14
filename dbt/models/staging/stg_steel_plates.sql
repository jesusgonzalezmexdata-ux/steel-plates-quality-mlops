-- Raw UCI CSV read as-is; the location is injected by tools/data_contract.py.
select *
from read_csv('{{ env_var("STEEL_RAW_CSV") }}', header = true, auto_detect = true)
