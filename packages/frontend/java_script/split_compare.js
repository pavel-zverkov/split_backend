console.log('green')

const table = document.querySelector('table');
const rows = table.rows;

for (let i = 1; i < rows.length; i++) {
    const row = rows[i];
    const resultCell = row.cells[3];

    if (resultCell.textContent.includes('-')) {
        resultCell.style.color = '#11ef0d';
    } else if (resultCell.textContent.includes('+')) {
        resultCell.style.color = '#f21e08';
    } else {

    }
}

