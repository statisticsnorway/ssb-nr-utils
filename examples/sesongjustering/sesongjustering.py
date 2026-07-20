from nr_utils.sesongjustering.x13 import *

import matplotlib.pyplot as plt


import os


df = pd.DataFrame(
    {
        "test_series":[
117.6321, 110.6025, 104.8950, 96.9695, 86.7018, 78.8318, 78.0121, 82.1642,
96.5159, 102.3555, 113.5752, 123.6357, 119.9755, 115.5377, 107.2848, 95.9743,
93.2637, 86.0345, 84.4102, 92.9304, 106.4474, 113.0026, 120.1865, 124.5225,
122.7044, 114.2969, 109.8878, 99.4937, 101.2351, 94.5265, 93.4225, 97.1657,
111.0839, 117.6951, 125.3150, 136.3268, 129.2745, 124.0235, 117.0190, 106.7959,
106.4826, 101.6068, 96.4737, 102.2382, 115.4476, 126.5961, 135.7104, 136.4260,
138.5409, 132.2199, 125.7574, 117.4867, 110.9020, 109.4147, 103.4894, 110.1698,
125.0512, 135.3186, 142.0268, 148.3604, 139.8691, 132.6253, 129.6352, 122.6646,
120.3349, 112.2253, 111.9255, 114.2364, 132.5346, 140.4152, 145.2409, 148.9917,
140.8448, 139.6680, 132.5025, 126.3962, 124.0231, 115.3350, 112.0360, 116.0306,
132.4485, 137.1384, 144.3527, 152.8708, 146.5735, 142.9108, 130.1298, 126.7866,
123.9890, 119.3467, 119.5382, 118.7328, 133.9700, 144.5159, 144.7231, 154.1961,
146.2567, 141.1788, 134.2238, 128.9506, 125.0671, 119.1353, 114.0103, 120.9332,
131.4628, 141.9426, 147.6159, 153.4491, 152.5089, 137.9397, 136.1164, 130.0892,
120.8811, 112.1872, 111.8570, 116.4022, 130.0293, 143.2727, 149.5855, 153.8786,
150.4865, 150.5271, 137.5098, 130.0893, 132.0464, 124.9229, 122.7883,
]
    }
)

df.index = pd.date_range(start="2016-01-01", periods=len(df), freq="MS")

df_s = run_x13_from_df(df= df, spec_folder="examples/sesongjustering/test_spec/")

df_s.index = pd.date_range(start="2016-01-01", periods=len(df), freq="MS")


fig, ax = plt.subplots(figsize=(12, 5))

ax.plot(df.index, df["test_series"], label="Original", color="tab:blue", alpha=0.6)
ax.plot(df_s["test_series_seasadj"].index, df_s["test_series_seasadj"], label="Seasonally adjusted (d11)", color="tab:red")
ax.plot(df_s["test_series_trend"].index, df_s["test_series_trend"], label="Trend (d12)", color="tab:green", linestyle="--")

ax.set_title("Original vs. X-13 Seasonally Adjusted")
ax.set_xlabel("Date")
ax.set_ylabel("Value")
ax.legend()
ax.grid(alpha=0.3)

plt.tight_layout()
plt.savefig("examples/sesongjustering/seasonal_adjustment_plot.png")


print(df_s.loc[df_s.index=="2016-01-01","test_series_seasadj"])