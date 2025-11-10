console.log("Ready (RTL Arabic UI).");

document.addEventListener("DOMContentLoaded", function() {
  // --- Theme Switcher ---
  const themeToggleButton = document.getElementById('theme-toggle');
  const lightIcon = document.getElementById('theme-icon-light');
  const darkIcon = document.getElementById('theme-icon-dark');
  const docElement = document.documentElement;

  // Function to apply theme
  function applyTheme(theme) {
    if (theme === 'dark') {
      docElement.setAttribute('data-theme', 'dark');
      if(lightIcon) lightIcon.style.display = 'none';
      if(darkIcon) darkIcon.style.display = 'block';
    } else {
      docElement.removeAttribute('data-theme');
      if(lightIcon) lightIcon.style.display = 'block';
      if(darkIcon) darkIcon.style.display = 'none';
    }
  }

  // Check for saved theme in localStorage or system preference
  const savedTheme = localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  applyTheme(savedTheme);

  // Add click listener to the toggle button
  if (themeToggleButton) {
    themeToggleButton.addEventListener('click', () => {
      const currentTheme = docElement.hasAttribute('data-theme') ? 'dark' : 'light';
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      localStorage.setItem('theme', newTheme);
      applyTheme(newTheme);
    });
  }
  // Format timestamps
  document.querySelectorAll("time").forEach(function(timeEl) {
    try {
      const date = new Date(timeEl.getAttribute("datetime"));
      // Format to something like: 25 ديسمبر 2023, 08:30 م
      timeEl.textContent = date.toLocaleString('ar-SA', { 
        year: 'numeric', month: 'long', day: 'numeric', 
        hour: 'numeric', minute: '2-digit', hour12: true 
      });
    } catch (e) {
      // Keep original text if date is invalid
    }
  });

  // User menu dropdown toggle
  const toggleButton = document.getElementById("user-menu-toggle");
  const dropdown = document.getElementById("user-menu-dropdown");

  if (toggleButton && dropdown) {
    toggleButton.addEventListener("click", function(event) {
      event.stopPropagation();
      dropdown.classList.toggle("show");
    });
  }

  // --- Submission Confirmation Modal ---
  const submissionForm = document.querySelector('form[action="/submit"]');
  const confirmationModal = document.getElementById('confirmation-modal');
  const modalText = document.getElementById('modal-text');
  const confirmBtn = document.getElementById('confirm-submit-btn');
  const cancelBtn = document.getElementById('cancel-submit-btn');
  const closeModalBtn = document.querySelector('.modal-close');

  if (submissionForm && confirmationModal) {
    submissionForm.addEventListener('submit', function(event) {
      event.preventDefault(); // Stop the form from submitting immediately
      const textToSubmit = submissionForm.querySelector('textarea[name="text"]').value;
      
      if (textToSubmit.trim() === "") return; // Don't show modal for empty text

      modalText.textContent = textToSubmit; // Show the user's text in the modal
      confirmationModal.style.display = 'flex'; // Show the modal
    });

    confirmBtn.addEventListener('click', () => {
      submissionForm.submit(); // Proceed with the original submission
    });

    const hideModal = () => { confirmationModal.style.display = 'none'; };
    cancelBtn.addEventListener('click', hideModal);
    closeModalBtn.addEventListener('click', hideModal);
  }

  // --- Interactive Admin Rubric ---
  const rubricForm = document.getElementById('rubric-form');
  if (rubricForm) {
    const finalGradeInput = document.getElementById('final-grade-input');
    const radioButtons = rubricForm.querySelectorAll('input[type="radio"]');
    const totalCriteria = new Set([...radioButtons].map(rb => rb.name)).size;
    const maxPossibleScore = totalCriteria * 4; // Each criterion is out of 4

    function updateFinalGrade() {
      let currentScore = 0;
      const checkedRadios = rubricForm.querySelectorAll('input[type="radio"]:checked');
      checkedRadios.forEach(radio => {
        currentScore += parseInt(radio.value, 10);
      });

      // Convert score to a grade out of 10
      const gradeOutOf10 = (currentScore / maxPossibleScore) * 10;
      finalGradeInput.value = gradeOutOf10.toFixed(1); // Format to one decimal place
    }

    radioButtons.forEach(radio => radio.addEventListener('change', updateFinalGrade));
  }
});