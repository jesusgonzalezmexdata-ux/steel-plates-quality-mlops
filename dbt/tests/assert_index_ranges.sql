-- Normalized indices of the UCI dataset: [0, 1], except orientation/luminosity in [-1, 1].
select id
from {{ ref('plate_defects') }}
where Edges_Index not between 0 and 1
   or Empty_Index not between 0 and 1
   or Square_Index not between 0 and 1
   or Outside_X_Index not between 0 and 1
   or Edges_X_Index not between 0 and 1
   or Edges_Y_Index not between 0 and 1
   or Outside_Global_Index not between 0 and 1
   or SigmoidOfAreas not between 0 and 1
   or Orientation_Index not between -1 and 1
   or Luminosity_Index not between -1 and 1
