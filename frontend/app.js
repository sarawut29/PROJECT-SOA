// URL หลักของ Django REST API
// URL หลักของ Django REST API (รองรับทั้ง localhost, Live Server และ Cloud Deploy)
const API_BASE = (window.location.protocol === 'file:' || window.location.port === '5500')
    ? 'http://127.0.0.1:8000/api'
    : `${window.location.origin}/api`;

// ดึง Elements สำคัญ
const authSection = document.getElementById('auth-section');
const dashboardSection = document.getElementById('dashboard-section');
const navUserSection = document.getElementById('nav-user-section');
const hrPanelSection = document.getElementById('hr-panel-section');
const formLogin = document.getElementById('form-login');
const formClaim = document.getElementById('form-claim');
const btnLogout = document.getElementById('btn-logout');
const btnRefreshClaims = document.getElementById('btn-refresh-claims');
const selectCategory = document.getElementById('claim-category');
const categoryHint = document.getElementById('category-hint');
const medicalCodeGroup = document.getElementById('group-medical-code');

let currentUser = null;
let cachedCategories = [];

// ==========================================
// 1. ตรวจสอบสถานะการเข้าสู่ระบบเมื่อเปิดเว็บ
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('access_token');
    if (token) {
        showDashboard();
    } else {
        showLoginForm();
    }
});

function showLoginForm() {
    authSection.style.display = 'block';
    dashboardSection.style.display = 'none';
    navUserSection.style.display = 'none';
}

function showDashboard() {
    authSection.style.display = 'none';
    dashboardSection.style.display = 'block';
    navUserSection.style.display = 'flex';
    
    // โหลดข้อมูล Dashboard
    loadUserProfile();
    loadCategories();
    loadClaimHistory();
}

// ==========================================
// 2. ระบบ Login ด้วย JWT (Lab 8 & Lab 10)
// ==========================================
formLogin.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    const alertBox = document.getElementById('login-alert');

    alertBox.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE}/auth/login/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });

        const data = await response.json();

        if (response.ok) {
            localStorage.setItem('access_token', data.access);
            localStorage.setItem('refresh_token', data.refresh);
            showDashboard();
        } else {
            alertBox.innerText = data.detail || 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง';
            alertBox.style.display = 'block';
        }
    } catch (err) {
        alertBox.innerText = 'ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ Backend ได้';
        alertBox.style.display = 'block';
    }
});

// ออกจากระบบ
btnLogout.addEventListener('click', () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    currentUser = null;
    showLoginForm();
});

// ==========================================
// 3. โหลดข้อมูล Profile & ตรวจสอบสิทธิ์ HR
// ==========================================
async function loadUserProfile() {
    const token = localStorage.getItem('access_token');
    try {
        const response = await fetch(`${API_BASE}/auth/profile/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.status === 401) {
            btnLogout.click();
            return;
        }

        currentUser = await response.json();
        document.getElementById('user-display-name').innerText = currentUser.username;
        document.getElementById('user-role-badge').innerText = currentUser.role;
        document.getElementById('user-balance').innerText = Number(currentUser.flex_point_balance).toLocaleString('th-TH', { minimumFractionDigits: 2 });
        document.getElementById('user-department').innerText = currentUser.department || '-';
        document.getElementById('user-policy').innerText = currentUser.policy_number || 'INS-GROUP-2026';

        // ตรวจสอบบทบาท: ถ้าเป็น HR_ADMIN ให้แสดงแผงตรวจสอบคำขอ (HR Approval Panel)
        if (currentUser.role === 'HR_ADMIN') {
            hrPanelSection.style.display = 'block';
            loadHRPendingClaims();
        } else {
            hrPanelSection.style.display = 'none';
        }
    } catch (err) {
        console.error('Error loading profile:', err);
    }
}

// ==========================================
// 4. โหลดหมวดหมู่สวัสดิการทั้ง 4 หมวดหลัก
// ==========================================
async function loadCategories() {
    const token = localStorage.getItem('access_token');
    try {
        const response = await fetch(`${API_BASE}/categories/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const result = await response.json();
        cachedCategories = result.results || result;

        selectCategory.innerHTML = '<option value="">-- กรุณาเลือกหมวดหมู่สวัสดิการ --</option>';
        cachedCategories.forEach(cat => {
            selectCategory.innerHTML += `<option value="${cat.id}">${cat.name}</option>`;
        });
    } catch (err) {
        console.error('Error loading categories:', err);
    }
}

selectCategory.addEventListener('change', () => {
    const selectedId = parseInt(selectCategory.value);
    const category = cachedCategories.find(c => c.id === selectedId);

    if (!category) {
        categoryHint.style.display = 'none';
        return;
    }

    if (category.requires_insurance_check) {
        categoryHint.innerHTML = `🩺 <strong>หมวดสุขภาพ:</strong> มีประกันกลุ่มคุ้มครอง 70% (สูงสุด ${category.max_limit_per_claim} บาท) ส่วนต่างจะหักจากแต้ม Flex Points เมื่อ HR อนุมัติ`;
        categoryHint.style.display = 'block';
        medicalCodeGroup.style.display = 'flex';
    } else {
        categoryHint.innerHTML = `💼 <strong>หมวดทั่วไป:</strong> ประกันไม่คุ้มครอง จะหักจากแต้ม Flex Points เต็มจำนวนเมื่อ HR อนุมัติ`;
        categoryHint.style.display = 'block';
        medicalCodeGroup.style.display = 'none';
    }
});

// ==========================================
// 5. ส่งคำขอยื่นเคลมสวัสดิการ (สถานะ PENDING)
// ==========================================
formClaim.addEventListener('submit', async (e) => {
    e.preventDefault();
    const token = localStorage.getItem('access_token');
    const resultBox = document.getElementById('claim-result-alert');

    const payload = {
        category_id: parseInt(selectCategory.value),
        title: document.getElementById('claim-title').value,
        receipt_number: document.getElementById('claim-receipt-number').value,
        receipt_amount: parseFloat(document.getElementById('claim-amount').value),
        medical_code: document.getElementById('claim-medical-code').value || ''
    };

    resultBox.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE}/claims/submit/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok) {
            resultBox.className = 'alert success';
            resultBox.innerHTML = `
                ⏳ <strong>${data.message}</strong><br>
                - เลขที่ใบเสร็จ: <strong>${data.claim.receipt_number || '-'}</strong><br>
                - ยอดตามใบเสร็จ: ${Number(data.claim.receipt_amount).toLocaleString()} บาท<br>
                - ประกันกลุ่มประเมินช่วยจ่าย: ${Number(data.claim.insurance_covered_amount).toLocaleString()} บาท<br>
                - แต้มที่จะถูกหักเมื่ออนุมัติ: ${Number(data.claim.receipt_amount - data.claim.insurance_covered_amount).toLocaleString()} แต้ม<br>
                - สถานะปัจจุบัน: <span class="badge badge-pending">PENDING</span> (รอ HR อนุมัติ)
            `;
            resultBox.style.display = 'block';
            formClaim.reset();
            categoryHint.style.display = 'none';

            // รีเฟรชตารางประวัติ และแผง HR (ถ้าล็อกอินเป็น HR)
            loadClaimHistory();
            if (currentUser && currentUser.role === 'HR_ADMIN') {
                loadHRPendingClaims();
            }
        } else {
            resultBox.className = 'alert error';
            resultBox.innerHTML = `❌ <strong>ยื่นเคลมไม่สำเร็จ:</strong> ${data.message || JSON.stringify(data)}`;
            resultBox.style.display = 'block';
        }
    } catch (err) {
        resultBox.className = 'alert error';
        resultBox.innerText = 'เกิดข้อผิดพลาดในการเชื่อมต่อ API';
        resultBox.style.display = 'block';
    }
});

// ==========================================
// 6. แผงควบคุมฝ่ายบุคคล (HR Review & Approval)
// ==========================================
async function loadHRPendingClaims() {
    const token = localStorage.getItem('access_token');
    const tableBody = document.getElementById('hr-pending-table-body');
    if (!tableBody) return;

    try {
        const response = await fetch(`${API_BASE}/claims/pending/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) return;

        const claims = await response.json();

        if (!claims || claims.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="10" class="text-center" style="color: #64748b;">✨ ยอดเยี่ยม! ไม่มีคำขอที่รอการอนุมัติในขณะนี้</td></tr>';
            return;
        }

        tableBody.innerHTML = '';
        claims.forEach(claim => {
            const dateStr = new Date(claim.created_at).toLocaleDateString('th-TH', {
                year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
            });

            const copay = (parseFloat(claim.receipt_amount) - parseFloat(claim.insurance_covered_amount)).toFixed(2);

            tableBody.innerHTML += `
                <tr>
                    <td>#${claim.id}</td>
                    <td><strong>${claim.user_name}</strong></td>
                    <td>${dateStr}</td>
                    <td><code>${claim.receipt_number || '-'}</code></td>
                    <td>${claim.title}</td>
                    <td>${claim.category_name}</td>
                    <td>${Number(claim.receipt_amount).toLocaleString()} ฿</td>
                    <td style="color: #16a34a;">${Number(claim.insurance_covered_amount).toLocaleString()} ฿</td>
                    <td style="color: #dc2626; font-weight: 600;">-${Number(copay).toLocaleString()}</td>
                    <td>
                        <div class="action-btns">
                            <button class="btn-sm-approve" onclick="approveClaim(${claim.id})">✅ อนุมัติ</button>
                            <button class="btn-sm-reject" onclick="rejectClaim(${claim.id})">❌ ปฏิเสธ</button>
                        </div>
                    </td>
                </tr>
            `;
        });
    } catch (err) {
        console.error('Error loading HR pending claims:', err);
    }
}

// ฟังก์ชัน HR กดอนุมัติ
window.approveClaim = async function(claimId) {
    if (!confirm(`ยืนยันการอนุมัติคำขอ #${claimId} และทำการตัดแต้มสวัสดิการของพนักงาน?`)) return;

    const token = localStorage.getItem('access_token');
    const hrAlert = document.getElementById('hr-action-alert');

    try {
        const response = await fetch(`${API_BASE}/claims/${claimId}/approve/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            }
        });

        const data = await response.json();

        if (response.ok) {
            hrAlert.className = 'alert success';
            hrAlert.innerText = `✅ ${data.message}`;
            hrAlert.style.display = 'block';
            loadHRPendingClaims();
            loadClaimHistory();
            loadUserProfile(); // อัปเดตแต้ม (กรณี HR อนุมัติคำขอของตัวเอง)
        } else {
            hrAlert.className = 'alert error';
            hrAlert.innerText = `❌ ${data.message || data.detail || 'อนุมัติไม่สำเร็จ'}`;
            hrAlert.style.display = 'block';
        }
    } catch (err) {
        alert('เกิดข้อผิดพลาดในการเชื่อมต่อเซิร์ฟเวอร์');
    }
};

// ฟังก์ชัน HR กดปฏิเสธ
window.rejectClaim = async function(claimId) {
    const reason = prompt("กรุณาระบุเหตุผลในการปฏิเสธคำขอนี้:", "ข้อมูลหรือเอกสารไม่ถูกต้องตามเงื่อนไข");
    if (reason === null) return; // กดยกเลิก prompt

    const token = localStorage.getItem('access_token');
    const hrAlert = document.getElementById('hr-action-alert');

    try {
        const response = await fetch(`${API_BASE}/claims/${claimId}/reject/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ reason: reason || 'เอกสารไม่ถูกต้อง' })
        });

        const data = await response.json();

        if (response.ok) {
            hrAlert.className = 'alert error';
            hrAlert.innerText = `⚠️ ${data.message}`;
            hrAlert.style.display = 'block';
            loadHRPendingClaims();
            loadClaimHistory();
        } else {
            alert(data.message || data.detail || 'ปฏิเสธคำขอไม่สำเร็จ');
        }
    } catch (err) {
        alert('เกิดข้อผิดพลาดในการเชื่อมต่อเซิร์ฟเวอร์');
    }
};

// ==========================================
// 7. โหลดประวัติการเคลมส่วนตัวของผู้ใช้ (My Claims)
// ==========================================
async function loadClaimHistory() {
    const token = localStorage.getItem('access_token');
    const tableBody = document.getElementById('claims-table-body');

    try {
        const response = await fetch(`${API_BASE}/claims/my-claims/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const claims = await response.json();

        if (!claims || claims.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="10" class="text-center">ยังไม่มีประวัติการยื่นเคลมของท่าน</td></tr>';
            return;
        }

        tableBody.innerHTML = '';
        claims.forEach(claim => {
            const dateStr = new Date(claim.created_at).toLocaleDateString('th-TH', {
                year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
            });

            let badgeClass = 'badge-pending';
            if (claim.status === 'APPROVED') badgeClass = 'badge-approved';
            if (claim.status === 'REJECTED') badgeClass = 'badge-rejected';

            tableBody.innerHTML += `
                <tr>
                    <td>#${claim.id}</td>
                    <td>${dateStr}</td>
                    <td><code>${claim.receipt_number || '-'}</code></td>
                    <td><strong>${claim.title}</strong></td>
                    <td>${claim.category_name}</td>
                    <td>${Number(claim.receipt_amount).toLocaleString()} ฿</td>
                    <td style="color: #16a34a;">${Number(claim.insurance_covered_amount).toLocaleString()} ฿</td>
                    <td style="color: #dc2626; font-weight: 600;">-${Number(claim.points_deducted).toLocaleString()}</td>
                    <td><span class="badge ${badgeClass}">${claim.status}</span></td>
                    <td style="font-size: 12px; color: #64748b;">${claim.remarks || '-'}</td>
                </tr>
            `;
        });
    } catch (err) {
        tableBody.innerHTML = '<tr><td colspan="10" class="text-center" style="color: red;">เกิดข้อผิดพลาดในการโหลดตาราง</td></tr>';
    }
}

btnRefreshClaims.addEventListener('click', () => {
    loadClaimHistory();
    if (currentUser && currentUser.role === 'HR_ADMIN') {
        loadHRPendingClaims();
    }
});
