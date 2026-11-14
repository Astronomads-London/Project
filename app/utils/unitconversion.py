CM_PER_INCH = 2.54
CM_PER_FOOT = 30.48
KG_PER_POUND = 0.45359237


def feet_to_cm(feet):
    """Convert feet to centimetres."""
    return feet * CM_PER_FOOT


def inches_to_cm(inches):
    """Convert inches to centimetres."""
    return inches * CM_PER_INCH


def height_to_cm(feet, inches=0):
    """Convert a height like 5 ft 10 in to centimetres."""
    return feet_to_cm(feet) + inches_to_cm(inches)


def pounds_to_kg(pounds):
    """Convert pounds to kilograms."""
    return pounds * KG_PER_POUND


def ask_float(question):
    """Keep asking until the user types a number that isn't negative."""
    while True:
        try:
            value = float(input(question))
        except ValueError:
            print("Please enter a number.")
            continue
        if value < 0:
            print("Please enter a number that isn't negative.")
            continue
        return value


if __name__ == "__main__":
    feet = ask_float("Enter height - feet: ")
    inches = ask_float("Enter height - inches: ")
    print(f"{feet:g} ft {inches:g} in = {height_to_cm(feet, inches):.2f} cm")

    pounds = ask_float("Enter weight in pounds: ")
    print(f"{pounds:g} lb = {pounds_to_kg(pounds):.2f} kg")
