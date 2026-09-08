# A4 Single-Page Exam Worksheet Layout Rules

## 1. Page Geometry & Canvas Limits
- **Page Size**: A4 (`595.27 pt x 841.89 pt`)
- **Margins**: Left/Right `38 pt`, Top `34 pt`, Bottom `28 pt`
- **Content Width**: `519.27 pt`
- **Header Structure**:
  - Title Font: `14.0 pt` (Bold gothic)
  - Subtitle/Name/Score: `9.5 pt`
  - Horizontal separator line: `1.0 pt` solid black
  - Header Bottom Gap: `26.0 pt`
- **Available Height for Questions**: `available_h = 841.89 - 34 - 8 - 26 - 28 = 745.89 pt`

## 2. Vertical Justification Algorithm (수직 균등 분배)
To ensure the worksheet fills exactly one A4 page without bottom voids or overflow:
1. Wrap text for each question's English sentence and calculate line count `N_en`.
2. Wrap text for each question's Korean translation and calculate line count `N_ko`.
3. Compute item height `H_item`:
   - **Test Sheet**: `H_item = (N_en * line_h_en) + 2.0 + blank_line_gap + 7.0` (with 2-line handwriting blanks)
   - **Answer Sheet**: `H_item = (N_en * line_h_en) + 2.0 + (N_ko * line_h_ko) + 3.0`
4. Compute total height: `total_items_h = sum(H_item for all questions)`
5. Compute dynamic gap between questions:
   \[
   \text{gap} = \frac{\text{available\_h} - \text{total\_items\_h}}{M - 1} \quad (M = \text{number of questions})
   \]
6. Render each question sequentially, placing subtle separator lines at `curr_y - (gap / 2.0)`.

## 3. Minimalist B&W Typography Guidelines
- **Palette**: Pure Black (`#000000`), Dark Gray (`#1F2937`), Underline Gray (`#777777`), Separator (`#E5E5E5`).
- **Font**: System standard Gothic (`AppleGothic.ttf` / `NanumGothic.ttf`).
- **Handwriting Blank**:
  - 1st line: Starts directly adjacent to `해석:` label to maximize horizontal space.
  - 2nd line: Spans the full content width.
  - Line gap: `18.5 pt` (ergonomic handwriting height for high school / college students).
