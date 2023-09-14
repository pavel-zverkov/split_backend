console.log('green')

const table = document.querySelector('table');
const rows = table.rows;

for (let i = 1; i < rows.length; i++) {
    const row = rows[i];
    const resultCell = row.cells[3];

    if (resultCell.textContent.includes('-')) {
        resultCell.style.color = 'rgba(0, 255, 0, 1)';
    } else if (resultCell.textContent.includes('+')) {
        resultCell.style.color = 'rgba(245, 0, 0, 1)';
    } else {

    }
}

