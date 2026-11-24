# quick test for model tools
# from root: python3 -m tests.try_model_tools

from agents.model_tools import train_model, evaluate_model, explain_model, predict
import itertools, threading, time, sys

def animate(text: str):
    for dots in itertools.cycle(["", ".", "..", "..."]):
        if done:
            break
        print(f"\r{text}{dots:<3}", end="", flush=True)
        time.sleep(0.4)
    print("\rDone!        ")

model = "test_logistic_reg"
data = "agent_data.student_por_clean"

done = False
t = threading.Thread(target=animate, args=("Training",))
t.start()
result = train_model("label", "LOGISTIC_REG", model)
done = True
t.join()
print(result)
if not result["ok"]:
    print("Stopping, step failed")
    sys.exit()

input("\n\nPress Enter to Evaluate the Model\n")

result = evaluate_model(model)
print(result)
if not result["ok"]:
    print("Stopping, step failed")
    sys.exit()

print("\n\nPress Enter to Explain the Model\n")
input()

result = explain_model(model, 5)
print(result)
if not result["ok"]:
    print("Stopping, step failed")
    sys.exit()

input("\n\nPress Enter to Predict with the Model\n")

result = predict(model, 3)
print(result)
