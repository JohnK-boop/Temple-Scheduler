# quick test for model tools
# run from repo root: python -m tests.try_model_tools

from agents.model_tools import train_model, evaluate_model, explain_model, predict

model = "test_logistic_reg"

result = train_model("agent_data.student_por", "passed", "LOGISTIC_REG", model, ["G1", "G2", "G3"])
print(result)

result = evaluate_model(model)
print(result)

result = explain_model(model, 5)
print(result)

result = predict(model, "agent_data.student_por", 3)
print(result)
