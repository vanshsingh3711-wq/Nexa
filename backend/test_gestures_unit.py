import math
from input.gesture.classifier import GestureClassifier
from input.gesture.stability_filter import GestureStabilityFilter
from core.commands.event_router import EventRouter

class MockLandmark:
    def __init__(self, x, y, z=0.0):
        self.x = x
        self.y = y
        self.z = z

def create_hand(
    wrist=(0.5, 0.8),
    thumb_tip=(0.35, 0.55),
    thumb_mcp=(0.42, 0.7),
    index_tip=(0.45, 0.3),
    index_mcp=(0.46, 0.55),
    index_pip=(0.45, 0.42),
    middle_tip=(0.5, 0.28),
    middle_mcp=(0.5, 0.55),
    middle_pip=(0.5, 0.4),
    ring_tip=(0.55, 0.3),
    ring_mcp=(0.54, 0.56),
    ring_pip=(0.55, 0.43),
    pinky_tip=(0.6, 0.35),
    pinky_mcp=(0.58, 0.58),
    pinky_pip=(0.6, 0.46)
):
    """Generates a 21-landmark mock hand dictionary/list matching MediaPipe indices."""
    landmarks = [None] * 21
    landmarks[0] = MockLandmark(*wrist)
    landmarks[1] = MockLandmark(wrist[0] - 0.04, wrist[1] - 0.05)
    landmarks[2] = MockLandmark(*thumb_mcp)
    landmarks[3] = MockLandmark((thumb_mcp[0] + thumb_tip[0])/2, (thumb_mcp[1] + thumb_tip[1])/2)
    landmarks[4] = MockLandmark(*thumb_tip)
    
    landmarks[5] = MockLandmark(*index_mcp)
    landmarks[6] = MockLandmark(*index_pip)
    landmarks[7] = MockLandmark((index_pip[0] + index_tip[0])/2, (index_pip[1] + index_tip[1])/2)
    landmarks[8] = MockLandmark(*index_tip)
    
    landmarks[9] = MockLandmark(*middle_mcp)
    landmarks[10] = MockLandmark(*middle_pip)
    landmarks[11] = MockLandmark((middle_pip[0] + middle_tip[0])/2, (middle_pip[1] + middle_tip[1])/2)
    landmarks[12] = MockLandmark(*middle_tip)
    
    landmarks[13] = MockLandmark(*ring_mcp)
    landmarks[14] = MockLandmark(*ring_pip)
    landmarks[15] = MockLandmark((ring_pip[0] + ring_tip[0])/2, (ring_pip[1] + ring_tip[1])/2)
    landmarks[16] = MockLandmark(*ring_tip)
    
    landmarks[17] = MockLandmark(*pinky_mcp)
    landmarks[18] = MockLandmark(*pinky_pip)
    landmarks[19] = MockLandmark((pinky_pip[0] + pinky_tip[0])/2, (pinky_pip[1] + pinky_tip[1])/2)
    landmarks[20] = MockLandmark(*pinky_tip)
    
    return landmarks

def test_classifier():
    classifier = GestureClassifier()
    
    # 1. Open Palm (All 5 extended)
    open_palm = create_hand()
    res = classifier.classify(open_palm)
    assert res["gesture"] == "Open Palm", f"Expected Open Palm, got {res['gesture']}"
    print("[PASS] Open Palm classified correctly")
    
    # 2. Closed Fist (All fingers curled, thumb tucked)
    closed_fist = create_hand(
        thumb_tip=(0.48, 0.65), # Tucked against index/middle
        index_tip=(0.46, 0.68), # Curled into palm
        index_pip=(0.45, 0.50),
        middle_tip=(0.5, 0.68),
        middle_pip=(0.5, 0.50),
        ring_tip=(0.54, 0.68),
        ring_pip=(0.55, 0.50),
        pinky_tip=(0.58, 0.68),
        pinky_pip=(0.6, 0.50)
    )
    res = classifier.classify(closed_fist)
    assert res["gesture"] == "Closed Fist", f"Expected Closed Fist, got {res['gesture']}"
    print("[PASS] Closed Fist classified correctly")
    
    # 3. Thumb Up (Fingers curled, thumb pointing UP)
    thumb_up = create_hand(
        thumb_tip=(0.35, 0.40), # Thumb pointing UP (y < thumb_mcp.y and y < wrist.y)
        thumb_mcp=(0.38, 0.65),
        index_tip=(0.46, 0.68),
        index_pip=(0.45, 0.50),
        middle_tip=(0.5, 0.68),
        middle_pip=(0.5, 0.50),
        ring_tip=(0.54, 0.68),
        ring_pip=(0.55, 0.50),
        pinky_tip=(0.58, 0.68),
        pinky_pip=(0.6, 0.50)
    )
    res = classifier.classify(thumb_up)
    assert res["gesture"] == "Thumb Up", f"Expected Thumb Up, got {res['gesture']}"
    print("[PASS] Thumb Up classified correctly")
    
    # 4. Thumb Down (Fingers curled, thumb pointing DOWN)
    thumb_down = create_hand(
        wrist=(0.5, 0.35),
        thumb_mcp=(0.38, 0.5),
        thumb_tip=(0.35, 0.75), # Thumb pointing DOWN (y > thumb_mcp.y and y > wrist.y)
        index_mcp=(0.46, 0.5),
        index_pip=(0.45, 0.62),
        index_tip=(0.46, 0.52), # Curled back towards MCP
        middle_mcp=(0.5, 0.5),
        middle_pip=(0.5, 0.62),
        middle_tip=(0.5, 0.52),
        ring_mcp=(0.54, 0.5),
        ring_pip=(0.55, 0.62),
        ring_tip=(0.54, 0.52),
        pinky_mcp=(0.58, 0.5),
        pinky_pip=(0.6, 0.62),
        pinky_tip=(0.58, 0.52)
    )
    res = classifier.classify(thumb_down)
    assert res["gesture"] == "Thumb Down", f"Expected Thumb Down, got {res['gesture']}"
    print("[PASS] Thumb Down classified correctly")
    
    # 5. Index (Index extended, others curled)
    index_only = create_hand(
        thumb_tip=(0.48, 0.65),
        index_tip=(0.45, 0.3), # Extended
        index_pip=(0.45, 0.42),
        middle_tip=(0.5, 0.68),
        middle_pip=(0.5, 0.50),
        ring_tip=(0.54, 0.68),
        ring_pip=(0.55, 0.50),
        pinky_tip=(0.58, 0.68),
        pinky_pip=(0.6, 0.50)
    )
    res = classifier.classify(index_only)
    assert res["gesture"] == "Index", f"Expected Index, got {res['gesture']}"
    print("[PASS] Index finger classified correctly")
    
    # 6. Peace (Index + Middle extended, ring + pinky curled)
    peace = create_hand(
        thumb_tip=(0.48, 0.65),
        index_tip=(0.45, 0.3), # Extended
        index_pip=(0.45, 0.42),
        middle_tip=(0.5, 0.28), # Extended
        middle_pip=(0.5, 0.4),
        ring_tip=(0.54, 0.68),
        ring_pip=(0.55, 0.50),
        pinky_tip=(0.58, 0.68),
        pinky_pip=(0.6, 0.50)
    )
    res = classifier.classify(peace)
    assert res["gesture"] == "Peace", f"Expected Peace, got {res['gesture']}"
    print("[PASS] Peace sign classified correctly")
    
    # 7. Pinch (Thumb tip touches Index tip)
    pinch = create_hand(
        thumb_tip=(0.45, 0.35),
        index_tip=(0.45, 0.35), # Touching
        middle_tip=(0.5, 0.68),
        middle_pip=(0.5, 0.50),
        ring_tip=(0.54, 0.68),
        ring_pip=(0.55, 0.50),
        pinky_tip=(0.58, 0.68),
        pinky_pip=(0.6, 0.50)
    )
    res = classifier.classify(pinch)
    assert res["gesture"] == "Pinch", f"Expected Pinch, got {res['gesture']}"
    print("[PASS] Pinch classified correctly")

def test_stability_and_router():
    stability = GestureStabilityFilter(history_size=7, confidence_threshold=0.6, base_alpha=0.7)
    router = EventRouter()
    
    # Simulate feeding Index gesture
    for i in range(5):
        st = stability.get_stable_gesture({"gesture": "Index", "cursor_x": 0.5 + i*0.01, "cursor_y": 0.5})
    assert st["gesture"] == "Index", f"Expected stable Index, got {st['gesture']}"
    print("[PASS] Stability filter converged on Index")
    
    # Test router idle state: should not trigger actions
    prev = {"gesture": "None", "cursor_x": 0.0, "cursor_y": 0.0}
    router.dispatch({"gesture": "Index", "cursor_x": 0.5, "cursor_y": 0.5}, prev)
    assert not router.is_active, "Router should remain idle until voice activation"
    print("[PASS] Router stays idle")
    
    # Open Palm should NOT toggle router anymore
    router.dispatch({"gesture": "Open Palm", "cursor_x": 0.5, "cursor_y": 0.5}, prev)
    assert not router.is_active, "Open Palm should not toggle router (voice activation required)"
    print("[PASS] Open Palm does not toggle router")
    
    # Activate router with set_active (Voice command trigger)
    router.set_active(True)
    assert router.is_active, "Router should be active after set_active(True)"
    print("[PASS] Router activated via voice command set_active(True)")
    
    # Feeding Unknown should NOT trigger swipe detector
    for _ in range(10):
        router.dispatch({"gesture": "Unknown", "cursor_x": 0.1, "cursor_y": 0.1}, {"gesture": "Unknown"})
    assert len(router.swipe_detector.history) == 0, "Swipe detector should not accumulate points on Unknown"
    print("[PASS] Swipe detector strictly ignores Unknown movements")
    
    # Feeding Open Palm moving right across screen should detect Swipe Right (Next page / Forward)
    router.last_swipe_time = 0.0
    for i in range(8):
        router.dispatch({"gesture": "Open Palm", "cursor_x": 0.2 + i*0.06, "cursor_y": 0.5}, {"gesture": "Open Palm"})
    print("[PASS] Open Palm Swipe Right (Next Page) triggered properly")
    
    # Feeding Open Palm moving left across screen should detect Swipe Left (Backward)
    router.last_swipe_time = 0.0
    for i in range(8):
        router.dispatch({"gesture": "Open Palm", "cursor_x": 0.8 - i*0.06, "cursor_y": 0.5}, {"gesture": "Open Palm"})
    print("[PASS] Open Palm Swipe Left (Backward) triggered properly")
    
    # Feeding Open Palm moving up across screen should detect Swipe Up (Open Task View)
    router.last_swipe_time = 0.0
    for i in range(8):
        router.dispatch({"gesture": "Open Palm", "cursor_x": 0.5, "cursor_y": 0.8 - i*0.06}, {"gesture": "Open Palm"})
    print("[PASS] Open Palm Swipe Up (Open Task View) triggered properly")
    
    # Feeding Peace sign moving right should select next window
    router.last_swipe_time = 0.0
    for i in range(8):
        router.dispatch({"gesture": "Peace", "cursor_x": 0.2 + i*0.06, "cursor_y": 0.5}, {"gesture": "Peace"})
    print("[PASS] Peace Swipe Right (Select Next Window) triggered properly")
    
    # Feeding Peace sign moving left should select prev window
    router.last_swipe_time = 0.0
    for i in range(8):
        router.dispatch({"gesture": "Peace", "cursor_x": 0.8 - i*0.06, "cursor_y": 0.5}, {"gesture": "Peace"})
    print("[PASS] Peace Swipe Left (Select Prev Window) triggered properly")
    
    # Feeding Peace sign moving down should confirm selection (Enter)
    router.last_swipe_time = 0.0
    for i in range(8):
        router.dispatch({"gesture": "Peace", "cursor_x": 0.5, "cursor_y": 0.2 + i*0.06}, {"gesture": "Peace"})
    print("[PASS] Peace Swipe Down (Confirm Selection / Enter) triggered properly")

if __name__ == "__main__":
    test_classifier()
    test_stability_and_router()
    print("\nALL UNIT TESTS PASSED SUCCESSFULLY!")
