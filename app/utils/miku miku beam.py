class SymptomChecker:
    def __init__(self):
        # A foundational knowledge base mapping illnesses to common symptoms
        self.knowledge_base = {
            "Common Cold": {"cough", "runny nose", "sore throat", "mild fever", "fatigue"},
            "Flu (Influenza)": {"high fever", "body aches", "fatigue", "dry cough", "chills", "headache"},
            "COVID-19": {"fever", "dry cough", "loss of taste", "loss of smell", "shortness of breath", "fatigue"},
            "Allergies": {"sneezing", "runny nose", "itchy eyes", "watery eyes"},
            "Strep Throat": {"sore throat", "fever", "swollen lymph nodes", "pain when swallowing"},
            "Gastroenteritis (Stomach Flu)": {"nausea", "vomiting", "diarrhea", "stomach cramps", "low-grade fever"}
        }

    def check_symptoms(self, user_symptoms):
        # Standardize user input to lowercase sets
        user_symptoms_set = set(symptom.lower().strip() for symptom in user_symptoms)
        results = []

        for illness, disease_symptoms in self.knowledge_base.items():
            # Calculate intersection between user symptoms and known disease symptoms
            matches = user_symptoms_set.intersection(disease_symptoms)

            if matches:
                # Calculate what percentage of the disease's standard symptoms are present
                match_percentage = (len(matches) / len(disease_symptoms)) * 100

                results.append({
                    "illness": illness,
                    "match_percentage": round(match_percentage, 2),
                    "matched_symptoms": list(matches),
                    "missing_symptoms": list(disease_symptoms - user_symptoms_set)
                })

        # Sort results descending by the highest match percentage
        results.sort(key=lambda x: x["match_percentage"], reverse=True)
        return results


# --- Example Implementation ---
if __name__ == "__main__":
    print("Start Checkup\n")

    system = SymptomChecker()

    # Simulated input from a patient questionnaire
    my_symptoms = ["fever", "fatigue", "dry cough", "body aches"]
    print(f"Patient reports: {my_symptoms}\n")

    diagnoses = system.check_symptoms(my_symptoms)

    if not diagnoses:
        print("No matching conditions found in the database.")
    else:
        print("Potential matches based on symptom overlap:")
        for result in diagnoses:
            print(f"- {result['illness']} ({result['match_percentage']}% match)")
            print(f"  Matched: {', '.join(result['matched_symptoms'])}")