const SYNC_URL = "PASTE_THE_OFFICE_SCRIPT_SYNC_URL_HERE";
const SOURCE_SHEETS = ["DQ Task Tracker", "Daily Report - FT", "Daily Report - BT"];

type CellValue = string | number | boolean;

async function main(workbook: ExcelScript.Workbook): Promise<void> {
  if (SYNC_URL === "PASTE_THE_OFFICE_SCRIPT_SYNC_URL_HERE") {
    throw new Error("Set SYNC_URL to the Office Script JSON Sync Endpoint from the Team Tracker Import page.");
  }

  const sheets: { [key: string]: CellValue[][] } = {};
  for (const sheetName of SOURCE_SHEETS) {
    const worksheet = workbook.getWorksheet(sheetName);
    if (!worksheet) {
      continue;
    }

    const usedRange = worksheet.getUsedRange();
    if (usedRange) {
      sheets[sheetName] = usedRange.getValues() as CellValue[][];
    }
  }

  if (Object.keys(sheets).length === 0) {
    throw new Error("None of the supported tracker sheets were found in this workbook.");
  }

  const response = await fetch(SYNC_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sheets, mode: "replace" }),
  });
  const responseText = await response.text();

  if (!response.ok) {
    throw new Error(`Team Tracker sync failed (${response.status}): ${responseText}`);
  }

  console.log(`Team Tracker sync completed: ${responseText}`);
}
