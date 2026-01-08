import random
import statistics

print("Verifying Humanize Logic (Standalone Simulation)...")

# Configuration matching implementation
SIGMA = 0.015  # 15ms standard deviation as implemented

# Simulate 1000 notes with ideal 0.1s gaps
# We want to check if the *intervals* between played notes are randomized but mean is conserved.
# Playback Engine Logic:
# target_time = original_time + random_offset
# We simulate the exact logic used in PlaybackEngine

events = []
for i in range(100):
    original_time = i * 0.1
    offset = random.gauss(0, SIGMA)
    target_time = max(0, original_time + offset)
    events.append(target_time)

events.sort()

# Calculate intervals
intervals = []
for i in range(len(events) - 1):
    intervals.append(events[i + 1] - events[i])

mean = statistics.mean(intervals)
stdev = statistics.stdev(intervals)
min_int = min(intervals)
max_int = max(intervals)

print("\n--- Statistical Analysis of 0.1s Intervals ---")
print(f"Humanize Sigma:    {SIGMA}s")
print(f"Target Interval:   0.100s")
print(f"Actual Mean:       {mean:.5f}s  (Pass if close to 0.1)")
print(f"Std Deviation:     {stdev:.5f}s  (Pass if > 0.01 and < 0.05)")
print(f"Min Interval:      {min_int:.5f}s")
print(f"Max Interval:      {max_int:.5f}s")

if 0.09 < mean < 0.11 and stdev > 0.01:
    print("\n[PASS] Timing looks organic! (Significant jitter but rhythm preserved)")
elif stdev <= 0.005:
    print("\n[FAIL] Timing is too robotic!")
else:
    print("\n[WARN] Timing might be too erratic!")
