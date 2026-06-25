# Sleep Journal & Sleep Factors Guide

The Sleep Journal and Sleep Factors system in `sleepstudy.app` allows you to track, correlate, and persist subjective qualitative variables alongside your biometric sleep stages and vitals. By cataloging positive **Sleep Aids**, negative **Sleep Disruptors**, sleep positions, and custom notes, you can easily identify what behaviors promote recovery and what triggers lead to high resting heart rate, lower HRV, and increased snoring/coughing.

---

## 1. Positive Sleep Aids vs. Negative Sleep Disruptors

To build a holistic view of your sleep hygiene, tags are divided into two distinct categories:

### A. Sleep Aids (Positive Impact)
These are interventions or tools used to improve breathing, comfort, or environment:
*   **Nose Strips**: Physically dilates nasal passages to reduce airway resistance and snoring.
*   **Eye Mask**: Blocks ambient light to promote melatonin production.
*   **Earplugs**: Attenuates ambient noise to prevent micro-arousals.
*   **Mouth Tape**: Encourages nasal breathing, reducing dry mouth and snoring.
*   **Humidifier**: Keeps nasal passages moist, preventing airway irritation.

### B. Sleep Disruptors (Negative Impact)
These are substances, habits, or conditions that impair sleep architecture and recovery:
*   **Alcohol**: Although it can reduce sleep latency, alcohol severely disrupts REM sleep (the restorative phase) in the second half of the night. It also acts as a muscle relaxant, increasing airway collapse (leading to heavier snoring) and elevating resting heart rate while suppressing Heart Rate Variability (HRV).
*   **Late Caffeine**: Blocks adenosine receptors (the chemical that builds "sleep pressure"). This delays sleep onset, reduces total sleep time, and diminishes slow-wave deep sleep.
*   **Late Heavy Meal / Sugar / Late Snack**: Elevates core body temperature (which must drop to initiate deep sleep) and triggers nocturnal digestion, which keeps heart rate high and can worsen acid reflux.
*   **Late Screen Time**: Blue light exposure suppresses melatonin secretion, delaying your circadian clock and reducing REM sleep.
*   **Stressful Evening**: Triggers cortisol and adrenaline release, keeping the sympathetic nervous system active, leading to shallow sleep and frequent awakenings.
*   **Late Intense Exercise**: Boosts core temperature and sympathetic drive if performed within 2-3 hours of bedtime, delaying sleep onset.

---

## 2. The Sleep Journal Interface

When you select any sleep session from the main dashboard, the **Sleep Journal** panel loads on the right side of the screen.

![Sleep Journal](./SleepJournal.png)

*   **Sleep Rating**: Subjective recovery quality from 1 to 5 stars.
*   **Sleep Position**: Primary sleep orientation (e.g., *Back*, *Left Side*, *Right Side*, *Stomach*, or *Mixed/Other*).
*   **Sleep Aids**: Click to toggle active aids. Selected aids glow **neon indigo**.
*   **Sleep Disruptors**: Click to toggle active disruptors. Selected disruptors glow **warning red**.
*   **Notes & Sleep Habits**: A freeform text field to log extra context (e.g., room temperature, specific stressors, timing details).

Click **Save Journal Entry** to write changes directly to the persistent SQLite database.

---

## 3. Managing Custom Tags (Sleep Factors Page)

You can customize the pool of available tags by navigating to the **Sleep Factors** tab (🩹 icon) in the left sidebar menu.

![Sleep Factors Configuration](./SleepAids.png)

### Adding a Tag
1. Enter a descriptive name in the input field.
2. Select the **Category** from the dropdown:
    *   **Sleep Aid (Positive)**
    *   **Sleep Disruptor (Negative)**
3. Click **Add Tag**. The new tag will immediately appear under the appropriate section in the Sleep Journal form.

### Deleting a Tag
*   Click the close (`x`) icon on any active pill under **Configured Sleep Aids** or **Configured Sleep Disruptors**.
*   *Note: Deleting a tag removes it from the configuration pool, but existing journal entries that already have this tag saved will retain it for historical accuracy.*

---

## 4. Database Storage & Schema Reference

Sleep journal data is stored inside your persistent SQLite volume (`/app/data/sleep_study.db`).

### Table: `sleep_sessions`
*   `rating` (Integer): Quality rating (1 to 5 stars).
*   `sleep_position` (String): Chosen dropdown option.
*   `sleep_aids` (String): Comma-separated list of active aid names (e.g., `Nose Strips,Mouth Tape`).
*   `sleep_disruptors` (String): Comma-separated list of active disruptor names (e.g., `Alcohol,Late Caffeine`).
*   `notes` (String): Text column for notes and annotations.

### Table: `sleep_aids`
*   `name` (String): Primary text identifier of the tag.
*   `category` (String): Category of the tag (`aid` or `disruptor`).
