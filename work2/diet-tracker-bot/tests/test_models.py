import math
from models import UserProfile

def test_bmr_tdee_light_male():
    prof = UserProfile(
        gender="male", age=25, height_cm=175, weight_kg=70, activity="light", target_kcal=None, macro_ratio={"carb":0.4,"protein":0.3,"fat":0.3}
    )
    bmr = prof.bmr()
    tdee = prof.tdee()
    # reference values
    assert math.isclose(bmr, 1668.75, rel_tol=0.01)
    assert math.isclose(tdee, 1668.75*1.375, rel_tol=0.01)


def test_macro_targets():
    prof = UserProfile(
        gender="male", age=25, height_cm=175, weight_kg=70, activity="light", target_kcal=1800, macro_ratio={"carb":0.4,"protein":0.3,"fat":0.3}
    )
    m = prof.macro_targets_g(1800)
    assert math.isclose(m["carb_g"], 1800*0.4/4.0, rel_tol=0.01)
    assert math.isclose(m["protein_g"], 1800*0.3/4.0, rel_tol=0.01)
    assert math.isclose(m["fat_g"], 1800*0.3/9.0, rel_tol=0.01)

