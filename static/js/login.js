document.addEventListener("DOMContentLoaded", function () {
    console.log("Sistema de Login de Cutupú - Inicializando");

    // ============================================
    // ELEMENTOS DEL DOM
    // ============================================
    const loginTab = document.getElementById("loginTab");
    const registerTab = document.getElementById("registerTab");
    const loginForm = document.getElementById("loginForm");
    const registerForm = document.getElementById("registerForm");
    const switchToLogin = document.getElementById("switchToLogin");
    const forgotPassword = document.getElementById("forgotPassword");

    // Formularios
    const loginFormElement = loginForm ? loginForm.querySelector("form") : null;
    const registerFormElement = registerForm ? registerForm.querySelector("form") : null;

    // ============================================
    // FUNCIONES DE TOGGLE
    // ============================================
    function showLogin() {
        if (!loginForm || !registerForm) return;
        
        loginForm.style.display = "block";
        registerForm.style.display = "none";

        if (loginTab) loginTab.classList.add("active");
        if (registerTab) registerTab.classList.remove("active");

        // Actualizar URL para navegación
        history.pushState({}, "", "/login");
        
        console.log("Mostrando formulario de Login");
    }

    function showRegister() {
        if (!loginForm || !registerForm) return;
        
        loginForm.style.display = "none";
        registerForm.style.display = "block";

        if (registerTab) registerTab.classList.add("active");
        if (loginTab) loginTab.classList.remove("active");

        // Actualizar URL para navegación
        history.pushState({}, "", "/login?form=register");
        
        console.log("Mostrando formulario de Registro");
        
        // Enfocar el primer campo del formulario de registro
        setTimeout(() => {
            const firstInput = registerForm.querySelector("input");
            if (firstInput) firstInput.focus();
        }, 100);
    }

    // ============================================
    // MANEJO DE FORMULARIO DE REGISTRO
    // ============================================
    function setupRegistrationForm() {
        if (!registerFormElement) {
            console.warn("Formulario de registro no encontrado");
            return;
        }

        // Verificar si el formulario ya tiene action y method
        if (!registerFormElement.getAttribute("action")) {
            registerFormElement.setAttribute("action", "/register");
            registerFormElement.setAttribute("method", "POST");
            console.log("Configurando action y method del formulario de registro");
        }

        // Agregar campos necesarios si no existen
        ensureRegistrationFields();

        // Agregar evento de submit
        registerFormElement.addEventListener("submit", function (e) {
            e.preventDefault(); // Prevenir envío normal para validar primero
            
            console.log("Enviando formulario de registro...");
            
            if (validateRegistrationForm()) {
                // Mostrar estado de carga
                const submitBtn = this.querySelector(".btn-submit");
                if (submitBtn) {
                    const originalText = submitBtn.innerHTML;
                    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creando cuenta...';
                    submitBtn.disabled = true;
                    
                    // Enviar formulario
                    console.log("Formulario válido, enviando...");
                    
                    // Crear FormData
                    const formData = new FormData(this);
                    
                    // Enviar por AJAX
                    fetch("/register", {
                        method: "POST",
                        body: formData,
                        headers: {
                            'Accept': 'application/json'
                        }
                    })
                    .then(response => {
                        console.log("Respuesta recibida:", response.status);
                        return response.text();
                    })
                    .then(data => {
                        console.log("Datos de respuesta:", data.substring(0, 200));
                        
                        // Verificar si hay redirección en la respuesta
                        if (data.includes('window.location') || data.includes('Redirecting')) {
                            // Si el servidor redirige, recargar la página
                            window.location.href = "/login";
                        } else {
                            // Insertar la respuesta en el documento
                            document.open();
                            document.write(data);
                            document.close();
                        }
                    })
                    .catch(error => {
                        console.error("Error en registro:", error);
                        submitBtn.innerHTML = originalText;
                        submitBtn.disabled = false;
                        alert("Error al crear la cuenta. Por favor intenta de nuevo.");
                    });
                }
            } else {
                console.log("Formulario de registro inválido");
                shakeForm(registerFormElement);
            }
        });

        console.log("Formulario de registro configurado");
    }

    // ============================================
    // VALIDACIÓN DE FORMULARIO DE REGISTRO
    // ============================================
    function validateRegistrationForm() {
        if (!registerFormElement) return false;
        
        console.log("Validando formulario de registro...");
        
        // Obtener campos
        const nombreInput = registerFormElement.querySelector('input[name="nombre"]');
        const emailInput = registerFormElement.querySelector('input[name="email"]');
        const passwordInput = registerFormElement.querySelector('input[name="password"]');
        const confirmPasswordInput = registerFormElement.querySelector('input[name="confirm_password"]');
        
        let isValid = true;
        
        // Limpiar errores anteriores
        clearFormErrors(registerFormElement);
        
        // Validar nombre
        if (nombreInput) {
            const nombre = nombreInput.value.trim();
            if (!nombre) {
                showFieldError(nombreInput, "El nombre completo es obligatorio");
                isValid = false;
            } else if (nombre.length < 3) {
                showFieldError(nombreInput, "El nombre debe tener al menos 3 caracteres");
                isValid = false;
            }
        }
        
        // Validar email
        if (emailInput) {
            const email = emailInput.value.trim();
            if (!email) {
                showFieldError(emailInput, "El correo electrónico es obligatorio");
                isValid = false;
            } else if (!isValidEmail(email)) {
                showFieldError(emailInput, "Ingrese un correo electrónico válido");
                isValid = false;
            }
        }
        
        // Validar contraseña
        if (passwordInput) {
            const password = passwordInput.value;
            if (!password) {
                showFieldError(passwordInput, "La contraseña es obligatoria");
                isValid = false;
            } else if (password.length < 6) {
                showFieldError(passwordInput, "La contraseña debe tener al menos 6 caracteres");
                isValid = false;
            }
        }
        
        // Validar confirmación de contraseña
        if (confirmPasswordInput && passwordInput) {
            const confirmPassword = confirmPasswordInput.value;
            const password = passwordInput.value;
            
            if (!confirmPassword) {
                showFieldError(confirmPasswordInput, "Debe confirmar la contraseña");
                isValid = false;
            } else if (confirmPassword !== password) {
                showFieldError(confirmPasswordInput, "Las contraseñas no coinciden");
                isValid = false;
            }
        }
        
        // Mostrar resumen de validación
        if (!isValid) {
            showFormError("Por favor corrige los errores en el formulario");
        }
        
        return isValid;
    }

    // ============================================
    // FUNCIONES AUXILIARES
    // ============================================
    function isValidEmail(email) {
        const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return regex.test(email);
    }

    function showFieldError(inputElement, message) {
        if (!inputElement) return;
        
        const formGroup = inputElement.closest(".form-group");
        if (!formGroup) return;
        
        // Agregar clase de error al input
        inputElement.classList.add("error");
        
        // Crear o actualizar mensaje de error
        let errorElement = formGroup.querySelector(".error-message");
        if (!errorElement) {
            errorElement = document.createElement("div");
            errorElement.className = "error-message";
            formGroup.appendChild(errorElement);
        }
        
        errorElement.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${message}`;
        errorElement.style.display = "block";
    }

    function showFormError(message) {
        // Crear mensaje de error general
        let errorContainer = registerForm.querySelector(".form-error");
        if (!errorContainer) {
            errorContainer = document.createElement("div");
            errorContainer.className = "form-error message error";
            registerForm.prepend(errorContainer);
        }
        
        errorContainer.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${message}`;
        errorContainer.style.display = "block";
        
        // Ocultar después de 5 segundos
        setTimeout(() => {
            errorContainer.style.display = "none";
        }, 5000);
    }

    function clearFormErrors(formElement) {
        if (!formElement) return;
        
        // Limpiar errores de campos
        const errorInputs = formElement.querySelectorAll(".error");
        errorInputs.forEach(input => input.classList.remove("error"));
        
        const errorMessages = formElement.querySelectorAll(".error-message");
        errorMessages.forEach(msg => msg.style.display = "none");
        
        // Limpiar error general
        const formError = formElement.querySelector(".form-error");
        if (formError) formError.style.display = "none";
    }

    function shakeForm(formElement) {
        formElement.style.animation = "shake 0.5s";
        setTimeout(() => {
            formElement.style.animation = "";
        }, 500);
    }

    function ensureRegistrationFields() {
        // Verificar que el formulario tenga todos los campos necesarios
        if (!registerFormElement) return;
        
        let fieldsAdded = false;
        
        // Agregar campo de nombre si no existe
        if (!registerFormElement.querySelector('input[name="nombre"]')) {
            const nombreGroup = document.createElement("div");
            nombreGroup.className = "form-group";
            nombreGroup.innerHTML = `
                <label>Nombre Completo</label>
                <input type="text" name="nombre" placeholder="Juan Pérez" required>
            `;
            registerFormElement.prepend(nombreGroup);
            fieldsAdded = true;
        }
        
        // Agregar campo de confirmación de contraseña si no existe
        if (!registerFormElement.querySelector('input[name="confirm_password"]')) {
            const passwordInput = registerFormElement.querySelector('input[name="password"]');
            if (passwordInput) {
                const confirmGroup = document.createElement("div");
                confirmGroup.className = "form-group";
                confirmGroup.innerHTML = `
                    <label>Confirmar Contraseña</label>
                    <input type="password" name="confirm_password" placeholder="Repita la contraseña" required>
                `;
                passwordInput.closest(".form-group").after(confirmGroup);
                fieldsAdded = true;
            }
        }
        
        // Agregar campo de email si no existe (usando el campo usuario como email)
        const usuarioInput = registerFormElement.querySelector('input[name="usuario"]');
        if (usuarioInput && !registerFormElement.querySelector('input[name="email"]')) {
            usuarioInput.name = "email";
            fieldsAdded = true;
        }
        
        if (fieldsAdded) {
            console.log("Campos del formulario de registro actualizados");
        }
    }

    // ============================================
    // MANEJO DE FORMULARIO DE LOGIN
    // ============================================
    function setupLoginForm() {
        if (!loginFormElement) return;
        
        console.log("Configurando formulario de login...");
        
        // Verificar que tenga action correcta
        if (!loginFormElement.getAttribute("action")) {
            loginFormElement.setAttribute("action", "/login");
        }
        
        // Agregar validación básica
        loginFormElement.addEventListener("submit", function(e) {
            const emailInput = this.querySelector('input[name="usuario"]');
            const passwordInput = this.querySelector('input[name="password"]');
            
            let hasError = false;
            clearFormErrors(this);
            
            // Validar email
            if (emailInput) {
                const email = emailInput.value.trim();
                if (!email) {
                    showFieldError(emailInput, "El correo electrónico es obligatorio");
                    hasError = true;
                } else if (!isValidEmail(email)) {
                    showFieldError(emailInput, "Ingrese un correo electrónico válido");
                    hasError = true;
                }
            }
            
            // Validar contraseña
            if (passwordInput && !passwordInput.value.trim()) {
                showFieldError(passwordInput, "La contraseña es obligatoria");
                hasError = true;
            }
            
            if (hasError) {
                e.preventDefault();
                shakeForm(loginFormElement);
            } else {
                // Mostrar loading
                const submitBtn = this.querySelector(".btn-submit");
                if (submitBtn) {
                    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Ingresando...';
                    submitBtn.disabled = true;
                }
            }
        });
    }

    // ============================================
    // EVENT LISTENERS
    // ============================================
    if (loginTab) {
        loginTab.addEventListener("click", function (e) {
            e.preventDefault();
            showLogin();
        });
    }

    if (registerTab) {
        registerTab.addEventListener("click", function (e) {
            e.preventDefault();
            showRegister();
        });
    }

    if (switchToLogin) {
        switchToLogin.addEventListener("click", function (e) {
            e.preventDefault();
            showLogin();
        });
    }

    if (forgotPassword) {
        forgotPassword.addEventListener("click", function (e) {
            e.preventDefault();
            const email = prompt("Ingrese su correo electrónico para recuperar la contraseña:");
            if (email && isValidEmail(email)) {
                alert(`Se ha enviado un enlace de recuperación a: ${email}\n\n(Esta funcionalidad está en desarrollo)`);
            } else if (email) {
                alert("Por favor ingrese un correo electrónico válido");
            }
        });
    }

    // ============================================
    // INICIALIZACIÓN
    // ============================================
    function initialize() {
        console.log("Inicializando sistema de login...");
        
        // Verificar parámetros de URL
        const urlParams = new URLSearchParams(window.location.search);
        const formType = urlParams.get('form');
        
        if (formType === 'register') {
            showRegister();
        } else {
            showLogin();
        }
        
        // Configurar formularios
        setupLoginForm();
        setupRegistrationForm();
        
        // Agregar estilos CSS dinámicos para errores
        addErrorStyles();
        
        console.log("Sistema de login inicializado correctamente");
    }

    function addErrorStyles() {
        // Agregar estilos CSS para errores si no existen
        if (!document.querySelector('#login-styles')) {
            const style = document.createElement('style');
            style.id = 'login-styles';
            style.textContent = `
                .error {
                    border-color: #dc2626 !important;
                    background-color: #fef2f2 !important;
                }
                
                .error-message {
                    color: #dc2626;
                    font-size: 0.85rem;
                    margin-top: 5px;
                    display: flex;
                    align-items: center;
                    gap: 5px;
                }
                
                .error-message i {
                    font-size: 0.9rem;
                }
                
                .form-error {
                    margin-bottom: 20px;
                    padding: 15px;
                    border-radius: 10px;
                    animation: fadeIn 0.3s ease;
                }
                
                @keyframes shake {
                    0%, 100% { transform: translateX(0); }
                    10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
                    20%, 40%, 60%, 80% { transform: translateX(5px); }
                }
                
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(-10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                
                .fa-spinner {
                    animation: spin 1s linear infinite;
                }
                
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
            `;
            document.head.appendChild(style);
        }
    }

    // Iniciar todo
    initialize();
});


/* ALERTA DE REGISTRO EXITOSO */
const params = new URLSearchParams(window.location.search);

if (params.get("registro") === "ok") {
    alert("✅ Cuenta creada con éxito. Ahora puedes iniciar sesión.");
}
