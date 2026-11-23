import data_agent

#print("Prepare:")
#print(data_agent.prepare())

#print("List Columns:")
#print(data_agent.list_input_columns())

#print("Normalize:")
#print(data_agent.normalize_column("G1"))

#print("Has null:")
#print(data_agent.has_null("G2"))

#print("Impute mean:")
#print(data_agent.impute_mean("G3"))

#print("Impute modes:")
#print(data_agent.impute_mode("Pstatus"))

#print("Copy column:")
#print(data_agent.copy_column("address"))

#print("Log column:")
#print(data_agent.logarithm_column("age"))

#print("Feature cross:")
#print(data_agent.feature_cross("freetime", True, "goout", True))

#print("Feature cross from output:")
#print(data_agent.feature_cross("age_log", False, "G1_normalized", False))

#print("Feature diff:")
#print(data_agent.feature_difference("freetime", True, "goout", True))

#print("Feature diff from output:")
#print(data_agent.feature_difference("age_log", False, "G1_normalized", False))

print("Numerical Encode:")
print(data_agent.numerical_encode_column("Mjob"))
