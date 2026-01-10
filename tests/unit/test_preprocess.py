from app.core.preprocess import compute_grid_size


def test_compute_grid_size_defaults():
    result = compute_grid_size(width=200, height=100, max_dim=120, grid_w=None, grid_h=None, lock_aspect=True)
    assert result.grid_w == 120
    assert result.grid_h == 60
    assert result.warnings == []


def test_compute_grid_size_clamp():
    result = compute_grid_size(width=200, height=100, max_dim=120, grid_w=200, grid_h=10, lock_aspect=False)
    assert result.grid_w == 120
    assert result.grid_h == 10
    assert any("clamped" in warning for warning in result.warnings)
