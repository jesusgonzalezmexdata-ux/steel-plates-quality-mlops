select id
from {{ ref('plate_defects') }}
where X_Maximum < X_Minimum
   or Y_Maximum < Y_Minimum
   or Pixels_Areas <= 0
   or Minimum_of_Luminosity > Maximum_of_Luminosity
   or Minimum_of_Luminosity < 0 or Maximum_of_Luminosity > 255
