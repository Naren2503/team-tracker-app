const SOURCE_SHEETS = ["DQ Task Tracker", "Daily Report - FT"];

type CellValue = string | number | boolean;

type SyncPayload = {
  sheets: { [key: string]: CellValue[][] };
  mode: "replace";
};

function main(workbook: ExcelScript.Workbook): SyncPayload {
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

  return { sheets, mode: "replace" };
}
