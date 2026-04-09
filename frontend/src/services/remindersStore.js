import { writable, get } from "svelte/store";

const STORAGE_KEY = "fixturecast_reminders";

function loadReminders() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const reminders = JSON.parse(stored);
      // Filter out expired reminders (past kickoff times)
      const now = Date.now();
      const active = reminders.filter(
        (r) => new Date(r.kickoffTime).getTime() > now,
      );
      if (active.length !== reminders.length) {
        saveReminders(active);
      }
      return active;
    }
  } catch (e) {
    console.error("Error loading reminders:", e);
  }
  return [];
}

function saveReminders(reminders) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(reminders));
  } catch (e) {
    console.error("Error saving reminders:", e);
  }
}

export const reminders = writable(loadReminders());

// Add a reminder for a fixture
export function addReminder(fixture) {
  reminders.update((current) => {
    // Check if already exists
    if (current.find((r) => r.fixtureId === fixture.fixtureId)) {
      return current;
    }

    const newReminder = {
      fixtureId: fixture.fixtureId,
      homeTeam: fixture.homeTeam,
      awayTeam: fixture.awayTeam,
      kickoffTime: fixture.kickoffTime,
      leagueName: fixture.leagueName || "Unknown League",
      createdAt: new Date().toISOString(),
    };

    const updated = [...current, newReminder];
    saveReminders(updated);

    // Schedule the notification
    scheduleNotification(newReminder);

    return updated;
  });
}

// Remove a reminder
export function removeReminder(fixtureId) {
  reminders.update((current) => {
    const updated = current.filter((r) => r.fixtureId !== fixtureId);
    saveReminders(updated);
    return updated;
  });
}

// Check if fixture has reminder
export function hasReminder(fixtureId) {
  const current = get(reminders);
  return current.some((r) => r.fixtureId === fixtureId);
}

// Toggle reminder for fixture
export function toggleReminder(fixture) {
  if (hasReminder(fixture.fixtureId)) {
    removeReminder(fixture.fixtureId);
    return false;
  } else {
    addReminder(fixture);
    return true;
  }
}

// Schedule notification 15 minutes before kickoff
function scheduleNotification(reminder) {
  const kickoffTime = new Date(reminder.kickoffTime).getTime();
  const reminderTime = kickoffTime - 15 * 60 * 1000; // 15 minutes before
  const now = Date.now();

  const delay = reminderTime - now;

  if (delay > 0 && delay < 24 * 60 * 60 * 1000) {
    // Only schedule if within 24 hours
    setTimeout(() => {
      showReminderNotification(reminder);
    }, delay);
  }
}

// Show the notification
async function showReminderNotification(reminder) {
  if (!("Notification" in window) || Notification.permission !== "granted") {
    return;
  }

  try {
    const registration = await navigator.serviceWorker.ready;

    registration.showNotification(
      `⚽ ${reminder.homeTeam} vs ${reminder.awayTeam}`,
      {
        body: `Kicks off in 15 minutes! ${reminder.leagueName}`,
        icon: "/icons/icon-192.png",
        badge: "/icons/icon-192.png",
        tag: `reminder-${reminder.fixtureId}`,
        data: {
          url: `/prediction/${reminder.fixtureId}`,
        },
        requireInteraction: true,
      },
    );
  } catch (e) {
    // Fallback to regular notification
    new Notification(`⚽ ${reminder.homeTeam} vs ${reminder.awayTeam}`, {
      body: `Kicks off in 15 minutes! ${reminder.leagueName}`,
      icon: "/icons/icon-192.png",
    });
  }

  // Remove the reminder after showing
  removeReminder(reminder.fixtureId);
}

// Initialize - schedule existing reminders on page load
export function initReminders() {
  const current = get(reminders);
  current.forEach((reminder) => {
    scheduleNotification(reminder);
  });
}
