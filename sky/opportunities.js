/**
 * opportunities.js — Qatar Foundation Admin Portal
 * Handles all opportunity management (US-2.1 to US-2.6)
 */
(function () {
  "use strict";

  // Auto-detects localhost vs live hosted URL
  const API_BASE = window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost"
    ? "http://127.0.0.1:5000/api"
    : window.location.origin + "/api";

  const getToken  = () => localStorage.getItem("qf_token");
  const clearAuth = () => {
    localStorage.removeItem("qf_token");
    localStorage.removeItem("qf_admin");
  };

  async function api(endpoint, options = {}) {
    const token = getToken();
    let res;
    try {
      res = await fetch(API_BASE + endpoint, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: "Bearer " + token } : {}),
        },
      });
    } catch (_) {
      throw { message: "Cannot reach server." };
    }
    const data = await res.json();
    if (res.status === 401) { clearAuth(); throw data; }
    if (!res.ok) throw data;
    return data;
  }

  const TO_BACKEND = {
    technology:"Technology", business:"Business", design:"Design",
    marketing:"Marketing",   data:"Data Science", other:"Other",
  };
  const TO_SELECT = {
    "Technology":"technology", "Business":"business", "Design":"design",
    "Marketing":"marketing",   "Data Science":"data", "Other":"other",
  };

  let editingId = null;

  const $   = id => document.getElementById(id);
  const val = id => { const el=$(id); return el ? el.value.trim() : ""; };

  /* ── Watch opportunity section */

  
  function watchSection() {
    const section = $("opportunitySection");
    if (!section) return;
    const observer = new MutationObserver(() => {
      if (section.classList.contains("active")) loadFromDB();
    });
    observer.observe(section, { attributes: true, attributeFilter: ["class"] });
  }

  /* ── Load from DB  */


  async function loadFromDB() {
    const grid = document.querySelector(".opportunities-grid");
    if (!grid) return;

    // Remove previously loaded DB cards only (keep static ones)
    grid.querySelectorAll(".opportunity-card[data-id]").forEach(c => c.remove());

    if (!getToken()) return;

    try {
      const data = await api("/opportunities/");
      const opps = data.data.opportunities || [];
      opps.forEach(opp => {
        const skills = opp.skills ? opp.skills.split(",").map(s=>s.trim()).filter(Boolean) : [];
        grid.appendChild(buildCard(opp, skills));
      });
    } catch (_) {}
  }

  /* ── Build card  */


  function buildCard(opp, skills) {
    const card = document.createElement("div");
    card.className = "opportunity-card";
    card.dataset.id = String(opp.id);
    card.innerHTML = `
      <div class="opportunity-card-header">
        <h5>${esc(opp.opportunity_name)}</h5>
        <div class="opportunity-meta">
          <span>
            <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/></svg>
            ${esc(opp.duration)}
          </span>
          <span>
            <svg viewBox="0 0 24 24">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
            <line x1="16" y1="2" x2="16" y2="6"/>
            <line x1="8" y1="2" x2="8" y2="6"/>
            <line x1="3" y1="10" x2="21" y2="10"/></svg>
            ${esc(opp.start_date)}
          </span>
          <span style="background:var(--qf-mint-pale);padding:2px 10px;border-radius:12px;
                       font-size:11px;font-weight:600;color:var(--qf-green-dark);">
            ${esc(opp.category)}
          </span>
        </div>
      </div>
      <p class="opportunity-description">${esc(opp.description)}</p>
      <div class="opportunity-skills">
        <div class="opportunity-skills-label">Skills You'll Gain</div>
        <div class="skills-tags">
          ${skills.map(s=>`<span class="skill-tag">${esc(s)}</span>`).join("")}
        </div>
      </div>
      <div class="opportunity-footer">
        <span class="applicants-count">
          ${opp.max_applicants ? opp.max_applicants+" applicants" : "0 applicants"}
        </span>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
          <button class="btn-opp-view view-course-btn"
                  style="width:auto;padding:8px 14px;">View Details</button>
          <button class="btn-opp-edit view-course-btn"
                  style="width:auto;padding:8px 14px;
                         background:linear-gradient(135deg,#1a6090,#2d8abf);">Edit</button>
          <button class="btn-opp-del view-course-btn"
                  style="width:auto;padding:8px 14px;
                         background:linear-gradient(135deg,#8b1a1a,#c0392b);">Delete</button>
        </div>
      </div>`;

    card.querySelector(".btn-opp-view").addEventListener("click", () => {
      openOpportunityDetails(opp.opportunity_name, {
        duration: opp.duration, startDate: opp.start_date,
        description: opp.description, skills, applicants: opp.max_applicants||0,
        futureOpportunities: opp.future_opportunities||"—", prerequisites:"—",
      });
    });
    card.querySelector(".btn-opp-edit").addEventListener("click", () => openEditForm(opp.id));
    card.querySelector(".btn-opp-del").addEventListener("click",  () => doDelete(opp.id, card));
    return card;
  }

  /* ── Form intercept (create + edit)  */


  document.addEventListener("submit", async function(e) {
    if (!e.target || e.target.id !== "opportunityForm") return;
    e.preventDefault();
    e.stopImmediatePropagation();
    await handleSubmit();
  }, true);

  async function handleSubmit() {
    const name=val("oppName"), duration=val("oppDuration"), startDate=val("oppStartDate"),
          description=val("oppDescription"), skillsRaw=val("oppSkills"),
          category=val("oppCategory"), future=val("oppFuture"), maxApp=val("oppMaxApplicants");

    if (!name||!duration||!startDate||!description||!skillsRaw||!category||!future) {
      showToast("Please fill in all required fields."); return;
    }

    const payload = {
      opportunity_name:name, category:TO_BACKEND[category]||category,
      duration, start_date:startDate, description, skills:skillsRaw,
      future_opportunities:future, max_applicants:maxApp?parseInt(maxApp):null,
    };

    try {
      if (editingId) {
        const data  = await api(`/opportunities/${editingId}`,{method:"PUT",body:JSON.stringify(payload)});
        const opp   = data.data.opportunity;
        const skills = skillsRaw.split(",").map(s=>s.trim()).filter(Boolean);
        const old   = document.querySelector(`[data-id="${editingId}"]`);
        if (old) old.replaceWith(buildCard(opp, skills));
        showToast("Opportunity updated successfully!");
      } else {
        const data  = await api("/opportunities/",{method:"POST",body:JSON.stringify(payload)});
        const opp   = data.data.opportunity;
        const skills = skillsRaw.split(",").map(s=>s.trim()).filter(Boolean);
        const grid  = document.querySelector(".opportunities-grid");
        if (grid) grid.appendChild(buildCard(opp, skills));
        showToast("Opportunity created successfully!");
      }
      resetForm();
      closeOpportunityModal();
    } catch(err) {
      if (err.status===401) { redirectToLogin(); return; }
      const msg=(err.errors&&err.errors.fields)?err.errors.fields.join(", "):(err.message||"Failed.");
      showToast("Error: "+msg);
    }
  }

  /* ── Open edit form  */


  async function openEditForm(oppId) {
    try {
      const data = await api(`/opportunities/${oppId}`);
      const opp  = data.data.opportunity;
      editingId  = opp.id;
      const modal = $("opportunityModal");
      if (modal) {
        const h3=modal.querySelector(".modal-header h3");
        const btn=modal.querySelector(".btn-primary");
        if(h3) h3.textContent="Edit Opportunity";
        if(btn) btn.textContent="Update Opportunity";
      }
      const map = {
        oppName:opp.opportunity_name, oppDuration:opp.duration,
        oppStartDate:opp.start_date,  oppDescription:opp.description,
        oppSkills:opp.skills||"",     oppCategory:TO_SELECT[opp.category]||"other",
        oppFuture:opp.future_opportunities||"",
        oppMaxApplicants:opp.max_applicants!=null?String(opp.max_applicants):"",
      };
      Object.entries(map).forEach(([id,value])=>{ const el=$(id); if(el) el.value=value; });
      openOpportunityModal();
    } catch(_) { showToast("Could not load opportunity."); }
  }

  /* ── Delete  */


  async function doDelete(oppId, cardEl) {
    if (!window.confirm("Delete this opportunity permanently? This cannot be undone.")) return;
    try {
      await api(`/opportunities/${oppId}`,{method:"DELETE"});
      cardEl.remove();
      showToast("Opportunity deleted.");
    } catch(err) {
      if(err.status===401){redirectToLogin();return;}
      showToast("Failed to delete.");
    }
  }

  /* ── Reset form  */


  function resetForm() {
    editingId=null;
    const form=$("opportunityForm"), modal=$("opportunityModal");
    if(form) form.reset();
    if(modal){
      const h3=modal.querySelector(".modal-header h3");
      const btn=modal.querySelector(".btn-primary");
      if(h3) h3.textContent="Add New Opportunity";
      if(btn) btn.textContent="Create Opportunity";
    }
  }

  const _origClose=window.closeOpportunityModal;
  window.closeOpportunityModal=function(){
    resetForm();
    if(typeof _origClose==="function") _origClose();
  };

  function redirectToLogin() {
    clearAuth();
    showToast("Session expired. Please log in again.");
    setTimeout(()=>{
      const dash=$("dashboardWrapper"), auth=$("authWrapper");
      if(dash) dash.classList.remove("active");
      if(auth) auth.style.display="flex";
      showPage("loginPage");
    },1500);
  }

  /* ── showDashboard override  */


  const _orig=window.showDashboard;
  window.showDashboard=function(email){
    if(typeof _orig==="function") _orig(email);
    try {
      const admin=JSON.parse(localStorage.getItem("qf_admin")||"{}");
      if(admin.full_name){
        const n=$("dashName"), a=$("dashAvatar");
        if(n) n.textContent=admin.full_name;
        if(a) a.textContent=admin.full_name.substring(0,2).toUpperCase();
      }
    } catch(_){}
  };

  function esc(s){
    return String(s||"")
      .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
      .replace(/"/g,"&quot;").replace(/'/g,"&#39;");
  }

  if(document.readyState==="loading"){
    document.addEventListener("DOMContentLoaded",watchSection);
  } else { watchSection(); }

  console.log("[opportunities.js] Loaded — API:", API_BASE);
})();