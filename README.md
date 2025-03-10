# Historical Rainfall Analysis for the Seattle Area

This project demonstrates how to use IBM's Environmental Intelligence APIs to determine and plot historical rainfall data for the Seattle area. The analysis covers the period from **April 1st, 2023 to September 30th, 2023**.

## Project Overview

The primary goal of this project is to showcase how to:
- Retrieve historical weather data using IBM's Environmental Intelligence APIs.
- Apply custom criteria to determine if rainfall occurred on a specific day.
- Classify the intensity of the rain (light vs. moderate/heavy) based on precipitation levels.
- Plot the rainfall data over the defined time period.

### Rain Determination Criteria

For each data point, the following criteria are used to determine the presence of rain:
1. **Temperature** should be greater than 0°C.
2. **Precipitation** should be greater than 0.
3. **Relative Humidity** should be greater than or equal to 70%.
4. **Dew Point** should be greater than 0°C.
5. **Rain Intensity Classification:**
   - If precipitation is less than 2.5, it is classified as **light rain**.
   - If precipitation is 2.5 or greater, it is classified as **moderate to heavy rain**.
