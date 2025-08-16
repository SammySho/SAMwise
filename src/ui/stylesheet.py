def get_group_box_style():
    return """
        QGroupBox {
            font-weight: bold;
            border: 1px solid gray;
            border-radius: 5px;
            margin-top: 6px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 3px;
        }
    """

def get_label_style():
    return """
        QLabel {
            font-size: 10pt;
        }
    """

def get_base_stylesheet():
    return "\n".join([
        get_group_box_style(),
        get_label_style(),
        # TODO: Add more component styles here
    ])