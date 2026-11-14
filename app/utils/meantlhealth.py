class Mentalhealth:
    """Scores one person's answers and turns the score into a concern level.

    Every answer adds points to ``healthnum`` (more points = more concern).
    ``healthlevel`` is the final category worked out from those points:
        0 = no concern, 1 = low, 2 = medium, 3 = high
    """

    def __init__(self, sleep, dailyslider, reactiontime, test, numnights=0):
        self.sleep = sleep
        self.dailyslider = dailyslider
        self.reactiontime = reactiontime
        self.test = test
        self.numnights = numnights  # nights in a row of short sleep (only asked if sleep < 6)
        self.healthnum = 0          # total points
        self.healthlevel = 0        # final category 0-3

    def sleepamount(self):
        if self.sleep < 6:
            if self.numnights >= 3:
                self.healthnum += 3
            else:
                self.healthnum += 2
        elif self.sleep < 7:
            self.healthnum += 2
        elif self.sleep < 9:
            self.healthnum += 1
        # 9+ hours adds nothing

    def dailysliderevaluation(self):
        self.healthnum += self.dailyslider

    def reactiontimeevaluation(self):
        # TODO: decide how reaction time should add points
        pass

    def testevaluation(self):
        # TODO: decide how the test score should add points
        pass

    def healthevaluation(self):
        """Run every check, then turn the total points into a level."""
        self.healthnum = 0
        self.sleepamount()
        self.dailysliderevaluation()
        self.reactiontimeevaluation()
        self.testevaluation()

        if self.healthnum < 4:
            self.healthlevel = 0
        elif self.healthnum < 7:
            self.healthlevel = 1
        elif self.healthnum < 10:
            self.healthlevel = 2
        else:
            self.healthlevel = 3
        return self.healthlevel


def askint(question, minimum=0):
    """Keep asking until the user types a whole number >= minimum."""
    while True:
        answer = input(question)
        try:
            value = int(answer)
        except ValueError:
            print("Please enter a whole number.")
            continue
        if value < minimum:
            print(f"Please enter a number of at least {minimum}.")
            continue
        return value


def main():
    mentalhealthlist = []

    while True:
        name = input("Please enter your name: ")
        sleep = askint("How many hours did you sleep? ")
        numnights = 0
        if sleep < 6:
            numnights = askint("How many nights in a row? ")
        dailyslider = askint("Enter your daily slider value: ")
        reactiontime = askint("Enter your reaction time: ")
        test = askint("Enter your test score: ")

        personhealth = Mentalhealth(sleep, dailyslider, reactiontime, test, numnights)
        level = personhealth.healthevaluation()
        mentalhealthlist.append([name, level])
        print(f"{name}: {personhealth.healthnum} points, level {level}\n")

        again = input("Add another person? (y/n): ").strip().lower()
        if again != "y":
            break

    print("\nResults:")
    for name, level in mentalhealthlist:
        print(f"  {name}: level {level}")


if __name__ == "__main__":
    main()
