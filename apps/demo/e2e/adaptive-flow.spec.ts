import { expect, test } from "@playwright/test";

test("applies a controlling patch before dependent values", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByText("Subsidiary legal name")).toHaveCount(0);
  await page.getByRole("button", { name: "Run guided sequence" }).click();

  await expect(page.getByText("Subsidiary legal name")).toBeVisible();
  await expect(page.getByText("IDFConfig r2")).toBeVisible();
  await expect(
    page.getByText(
      "Supervisor → User: subsidiary details completed with no unresolved items.",
    ),
  ).toBeVisible();
  await expect(page.locator('input[value="Acme UK Ltd"]')).toBeVisible();
  await expect(page.locator("select").nth(1)).toHaveValue("GB");
});
