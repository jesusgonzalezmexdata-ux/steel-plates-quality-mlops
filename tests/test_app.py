from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "streamlit_app.py")


def test_app_corre_sin_excepciones_y_muestra_kpis():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    valores = {m.label: m.value for m in at.metric}
    assert valores["Placas defectuosas"] == "1,941"
    assert valores["COPQ (supuesto)"] == "2.24 M MXN"


def test_app_con_filtro_que_vacia_los_datos_no_falla():
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.multiselect[0].set_value([])
    at.run()
    assert not at.exception and at.warning
