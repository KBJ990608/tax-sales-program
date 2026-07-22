const prospectForm = document.getElementById('prospectForm');
const prospectTableBody = document.querySelector('#prospectTable tbody');
const clearFormButton = document.getElementById('clearForm');
const generatePitchButton = document.getElementById('generatePitch');
const generatePromptButton = document.getElementById('generatePrompt');
const generateChecklistButton = document.getElementById('generateChecklist');
const exportCsvButton = document.getElementById('exportCsvButton');
const selectedProspectDiv = document.getElementById('selectedProspect');
const summaryOutput = document.getElementById('summaryOutput');
const pitchOutput = document.getElementById('pitchOutput');
const promptOutput = document.getElementById('promptOutput');
const checklistOutput = document.getElementById('checklistOutput');

let prospects = [];
let selectedIndex = null;

function renderProspects() {
  prospectTableBody.innerHTML = '';

  prospects.forEach((prospect, index) => {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${prospect.companyName || '-'}</td>
      <td>${prospect.industry || '-'}</td>
      <td>${prospect.size || '-'}</td>
      <td>${prospect.contactInfo || '-'}</td>
      <td>${prospect.painPoints || '-'}</td>
      <td>${prospect.status || '신규'}</td>
      <td>
        <button data-action="select" data-index="${index}">선택</button>
        <button data-action="delete" data-index="${index}">삭제</button>
      </td>
    `;
    prospectTableBody.appendChild(row);
  });
}

function clearForm() {
  prospectForm.reset();
}

function selectProspect(index) {
  selectedIndex = index;
  const prospect = prospects[index];
  selectedProspectDiv.textContent = `상호: ${prospect.companyName}\n업종: ${prospect.industry || '미입력'}\n규모: ${prospect.size || '미입력'}\n담당자: ${prospect.contactInfo || '미입력'}\n핵심 이슈: ${prospect.painPoints || '미입력'}\n리서치: ${prospect.researchNotes || '미입력'}\n메모: ${prospect.notes || '미입력'}`;
  generatePitchButton.disabled = false;
  generatePromptButton.disabled = false;
  generateChecklistButton.disabled = false;
  summaryOutput.textContent = '';
  pitchOutput.textContent = '';
  promptOutput.textContent = '';
  checklistOutput.textContent = '';
}

function deleteProspect(index) {
  prospects.splice(index, 1);
  if (selectedIndex === index) {
    selectedIndex = null;
    selectedProspectDiv.textContent = '대상을 선택하면 요약과 메시지를 생성합니다.';
    generatePitchButton.disabled = true;
    generatePromptButton.disabled = true;
    summaryOutput.textContent = '';
    pitchOutput.textContent = '';
    promptOutput.textContent = '';
  }
  renderProspects();
}

function generateSummary(prospect) {
  const summaryParts = [];
  summaryParts.push(`상호: ${prospect.companyName}`);
  if (prospect.industry) summaryParts.push(`업종: ${prospect.industry}`);
  if (prospect.size) summaryParts.push(`규모/매출: ${prospect.size}`);
  if (prospect.painPoints) summaryParts.push(`관심 분야/이슈: ${prospect.painPoints}`);
  if (prospect.researchNotes) summaryParts.push(`Google 리서치 요약: ${prospect.researchNotes}`);
  return summaryParts.join('\n');
}

function generateSalesPitch(prospect) {
  const pitch = [];
  pitch.push(`안녕하세요, ${prospect.companyName} 담당자님.`);
  pitch.push(`저희는 ${prospect.industry || '귀사 업종'}에 특화된 세무 전문 그룹입니다.`);
  pitch.push(`현재 ${prospect.painPoints || '세무 관리, 신고, 감사 대응'} 분야에서 효과적인 비용 절감과 리스크 관리를 도와드립니다.`);
  if (prospect.size) pitch.push(`특히 ${prospect.size} 규모의 기업에 맞춘 맞춤형 서비스로, 세무조사 대비와 세무조정 실행을 빠르게 지원할 수 있습니다.`);
  pitch.push(`구체적으로는 매출/비용 처리, 급여세, 원천세, 법인세 신고, 부가세 신고, 세무조사 대응까지 통합적으로 관리해 드립니다.`);
  pitch.push(`귀사의 현재 이슈 정보(${prospect.painPoints || '기재해 주신 사항'})를 바탕으로, 부담 없는 비용으로 안정적인 세무 운영을 제안드립니다.`);
  pitch.push(`편하신 시간에 상담 일정을 조율해 주시면, 정확한 절세 전략과 현장 지원 방안을 안내드리겠습니다.`);
  return pitch.join('\n\n');
}

function generateLLMPrompt(prospect) {
  return `당신은 한국 세무사 영업 담당자입니다. 다음 정보를 바탕으로 잠재 고객에게 보낼 영업 이메일 형식의 문장을 작성하세요.

상호: ${prospect.companyName}
업종: ${prospect.industry || '미입력'}
규모/매출: ${prospect.size || '미입력'}
담당자/연락처: ${prospect.contactInfo || '미입력'}
핵심 이슈: ${prospect.painPoints || '미입력'}
구글 리서치 요약: ${prospect.researchNotes || '미입력'}
메모: ${prospect.notes || '미입력'}

요청:
1. 첫인사와 신뢰성을 담아 간결하게 작성
2. 고객의 이슈에 공감하고 해결 방안을 제안
3. 세무사로서의 전문성과 세무 리스크 감소, 절세 포인트를 포함
4. 상담 요청과 연락 제안으로 마무리

출력 형식:
- 문단 3~4개
- 문체는 공손하고 전문적
- 최대 250자 내외
`;}

function generateChecklist(prospect) {
  const items = [
    `1. 고객 업종(${prospect.industry || '미입력'})의 주요 세무 리스크 확인`,
    `2. 연매출/규모(${prospect.size || '미입력'})에 맞춘 세무대행 범위 제안`,
    `3. 핵심 이슈(${prospect.painPoints || '미입력'}) 기반 맞춤 상담 구성`,
    `4. 세무조사 대비, 부가세/법인세 신고, 원천세/급여 관리 포함 여부 확인`,
    `5. 기존 세무사 이력 및 교체 시 인수인계 계획 수립`,
    `6. 추가 상담 시 필요한 자료(매출자료, 비용증빙, 고용현황) 요청`,
    `7. 추후 follow-up 일정 및 담당자 연락처 정리`,
  ];
  return `세무 영업 체크리스트:\n${items.join('\n')}`;
}

prospectForm.addEventListener('submit', (event) => {
  event.preventDefault();
  const newProspect = {
    companyName: document.getElementById('companyName').value.trim(),
    industry: document.getElementById('industry').value.trim(),
    size: document.getElementById('size').value.trim(),
    contactInfo: document.getElementById('contactInfo').value.trim(),
    painPoints: document.getElementById('painPoints').value.trim(),
    researchNotes: document.getElementById('researchNotes').value.trim(),
    notes: document.getElementById('notes').value.trim(),
    status: '신규',
  };

  prospects.push(newProspect);
  saveProspects();
  clearForm();
  renderProspects();
});

clearFormButton.addEventListener('click', clearForm);

prospectTableBody.addEventListener('click', (event) => {
  const action = event.target.dataset.action;
  const index = Number(event.target.dataset.index);
  if (action === 'select') selectProspect(index);
  if (action === 'delete') {
    deleteProspect(index);
    saveProspects();
  }
});

generatePitchButton.addEventListener('click', () => {
  if (selectedIndex === null) return;
  const prospect = prospects[selectedIndex];
  const summary = generateSummary(prospect);
  const pitch = generateSalesPitch(prospect);
  summaryOutput.textContent = summary;
  pitchOutput.textContent = pitch;
});

generatePromptButton.addEventListener('click', () => {
  if (selectedIndex === null) return;
  const prospect = prospects[selectedIndex];
  promptOutput.textContent = generateLLMPrompt(prospect);
});

generateChecklistButton.addEventListener('click', () => {
  if (selectedIndex === null) return;
  const prospect = prospects[selectedIndex];
  checklistOutput.textContent = generateChecklist(prospect);
});

exportCsvButton.addEventListener('click', () => {
  exportToCsv();
});

document.querySelectorAll('.copy-button').forEach((button) => {
  button.addEventListener('click', (event) => {
    const target = event.target.dataset.target;
    const content = document.getElementById(target).textContent;
    if (!content) return;
    navigator.clipboard.writeText(content).then(() => {
      button.textContent = '복사 완료';
      setTimeout(() => {
        button.textContent = '복사';
      }, 1200);
    });
  });
});

function saveProspects() {
  localStorage.setItem('taxSalesProspects', JSON.stringify(prospects));
}

function loadProspects() {
  const saved = localStorage.getItem('taxSalesProspects');
  if (!saved) return;
  prospects = JSON.parse(saved);
}

function exportToCsv() {
  const rows = [
    ['상호', '업종', '규모', '담당자/연락처', '이슈', '리서치', '메모', '상태'],
    ...prospects.map((prospect) => [
      prospect.companyName,
      prospect.industry,
      prospect.size,
      prospect.contactInfo,
      prospect.painPoints,
      prospect.researchNotes,
      prospect.notes,
      prospect.status,
    ]),
  ];

  const csvContent = rows
    .map((row) => row.map((item) => `"${String(item || '').replace(/"/g, '""')}"`).join(','))
    .join('\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', 'tax_sales_prospects.csv');
  link.click();
  URL.revokeObjectURL(url);
});

loadProspects();
