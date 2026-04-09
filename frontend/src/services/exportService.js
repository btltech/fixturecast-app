import { get } from "svelte/store";
import { _, locale } from "svelte-i18n";
import { formatDate } from "../lib/i18n/format.js";

function t(key, values) {
  return get(_)(key, values ? { values } : undefined);
}

export function exportPredictionsToCSV(predictions) {
  if (!Array.isArray(predictions) || predictions.length === 0) {
    return { ok: false, message: t("export.noPredictions") };
  }

  const headers = [
    t("export.headers.date"),
    t("export.headers.homeTeam"),
    t("export.headers.awayTeam"),
    t("export.headers.homeWin"),
    t("export.headers.draw"),
    t("export.headers.awayWin"),
    t("export.headers.predictedScore"),
    t("export.headers.btts"),
    t("export.headers.over25"),
    t("export.headers.confidence"),
  ];

  const currentLocale = get(locale);

  const rows = predictions.map((pred) => [
    pred.date || formatDate(new Date(), currentLocale, {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }),
    pred.home_team || "",
    pred.away_team || "",
    ((pred.home_win_prob || 0) * 100).toFixed(1),
    ((pred.draw_prob || 0) * 100).toFixed(1),
    ((pred.away_win_prob || 0) * 100).toFixed(1),
    pred.predicted_scoreline || "",
    ((pred.btts_prob || 0) * 100).toFixed(1),
    ((pred.over25_prob || 0) * 100).toFixed(1),
    ((pred.confidence || 0) * 100).toFixed(1),
  ]);

  const csvContent = [
    headers.join(","),
    ...rows.map((row) => row.map((cell) => `"${cell}"`).join(",")),
  ].join("\n");

  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);

  link.setAttribute("href", url);
  link.setAttribute(
    "download",
    `fixturecast_predictions_${new Date().toISOString().split("T")[0]}.csv`,
  );
  link.style.visibility = "hidden";

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);

  return {
    ok: true,
    message: t("export.csvDownloaded", { count: predictions.length }),
  };
}

export function exportPredictionsToPDF(predictions) {
  if (!Array.isArray(predictions) || predictions.length === 0) {
    return { ok: false, message: t("export.noPredictions") };
  }

  const currentLocale = get(locale);

  // Create a printable HTML page
  const content = `
<!DOCTYPE html>
<html>
<head>
  <title>${t("export.pdfTitle")}</title>
  <style>
    body { font-family: Arial, sans-serif; padding: 20px; }
    h1 { color: #8b5cf6; border-bottom: 2px solid #8b5cf6; padding-bottom: 10px; }
    table { width: 100%; border-collapse: collapse; margin-top: 20px; }
    th { background: #8b5cf6; color: white; padding: 10px; text-align: left; }
    td { padding: 10px; border-bottom: 1px solid #ddd; }
    tr:hover { background: #f5f5f5; }
    .footer { margin-top: 30px; font-size: 12px; color: #666; }
  </style>
</head>
<body>
  <h1>${t("export.pdfHeading")}</h1>
  <p>${t("export.generated")}: ${formatDate(new Date(), currentLocale, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })}</p>
  <table>
    <thead>
      <tr>
        <th>${t("export.headers.match")}</th>
        <th>${t("export.headers.homeWin")}</th>
        <th>${t("export.headers.draw")}</th>
        <th>${t("export.headers.awayWin")}</th>
        <th>${t("export.headers.score")}</th>
        <th>${t("export.headers.confidence")}</th>
      </tr>
    </thead>
    <tbody>
      ${predictions
        .map(
          (pred) => `
        <tr>
          <td>${pred.home_team} ${t("common.vs")} ${pred.away_team}</td>
          <td>${((pred.home_win_prob || 0) * 100).toFixed(1)}%</td>
          <td>${((pred.draw_prob || 0) * 100).toFixed(1)}%</td>
          <td>${((pred.away_win_prob || 0) * 100).toFixed(1)}%</td>
          <td>${pred.predicted_scoreline || t("export.notAvailable")}</td>
          <td>${((pred.confidence || 0) * 100).toFixed(0)}%</td>
        </tr>
      `,
        )
        .join("")}
    </tbody>
  </table>
  <div class="footer">
    <p>${t("export.footerTitle")}</p>
    <p>${t("export.footerSubtitle")}</p>
  </div>
</body>
</html>
  `;

  const printWindow = window.open("", "_blank");

  // Handle popup blocker
  if (!printWindow) {
    return {
      ok: false,
      message: t("export.popupBlocked"),
    };
  }

  printWindow.document.write(content);
  printWindow.document.close();
  printWindow.focus();
  printWindow.onload = () => {
    printWindow.print();
    printWindow.close();
  };

  return {
    ok: true,
    message: t("export.printOpened"),
  };
}
