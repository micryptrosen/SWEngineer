def test_gui_imports_only():
    # Import surface must be safe and side-effect free (no QApplication created here).
    import app.gui.main  # noqa: F401
    import app.gui  # noqa: F401
