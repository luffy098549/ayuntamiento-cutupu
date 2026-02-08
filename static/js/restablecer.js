
        document.addEventListener('DOMContentLoaded', function() {
            // Auto-focus en el primer campo
            const passwordField = document.getElementById('password');
            if (passwordField) {
                passwordField.focus();
            }
            
            // Manejo del envío del formulario
            const form = document.getElementById('resetForm');
            const submitBtn = document.getElementById('submitBtn');
            
            if (form && submitBtn) {
                form.addEventListener('submit', function(e) {
                    // Validar contraseñas
                    const password = document.getElementById('password').value;
                    const confirmPassword = document.getElementById('confirm_password').value;
                    
                    if (password.length < 6) {
                        e.preventDefault();
                        alert('La contraseña debe tener al menos 6 caracteres');
                        passwordField.focus();
                        return;
                    }
                    
                    if (password !== confirmPassword) {
                        e.preventDefault();
                        alert('Las contraseñas no coinciden');
                        document.getElementById('confirm_password').focus();
                        return;
                    }
                    
                    // Cambiar estado del botón
                    const originalHTML = submitBtn.innerHTML;
                    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
                    submitBtn.disabled = true;
                });
            }
            
            // Event listeners para validación en tiempo real
            const passwordInput = document.getElementById('password');
            const confirmInput = document.getElementById('confirm_password');
            
            if (passwordInput) {
                passwordInput.addEventListener('input', function() {
                    checkPasswordStrength();
                    checkPasswordMatch();
                });
            }
            
            if (confirmInput) {
                confirmInput.addEventListener('input', checkPasswordMatch);
            }
            
            // Inicializar validación
            checkPasswordStrength();
            checkPasswordMatch();
        });
        
        // Mostrar/ocultar contraseña
        function togglePasswordVisibility(fieldId) {
            const field = document.getElementById(fieldId);
            const toggleBtn = field.nextElementSibling.querySelector('i');
            
            if (field.type === 'password') {
                field.type = 'text';
                toggleBtn.className = 'fas fa-eye-slash';
            } else {
                field.type = 'password';
                toggleBtn.className = 'fas fa-eye';
            }
        }
        
        // Verificar fortaleza de contraseña
        function checkPasswordStrength() {
            const password = document.getElementById('password').value;
            const strengthBar = document.getElementById('strengthBar');
            const strengthText = document.getElementById('strengthText');
            
            if (!password) {
                strengthBar.style.width = '0%';
                strengthText.textContent = 'Escribe tu contraseña';
                strengthText.style.color = '#666';
                resetRules();
                return;
            }
            
            let strength = 0;
            
            // Reglas
            const hasLength = password.length >= 6;
            const hasUpperCase = /[A-Z]/.test(password);
            const hasLowerCase = /[a-z]/.test(password);
            const hasNumbers = /\d/.test(password);
            
            // Actualizar indicadores visuales de reglas
            updateRule('ruleLength', hasLength);
            updateRule('ruleUpper', hasUpperCase);
            updateRule('ruleLower', hasLowerCase);
            updateRule('ruleNumber', hasNumbers);
            
            // Calcular fortaleza
            if (password.length >= 6) strength += 25;
            if (password.length >= 8) strength += 25;
            if (hasUpperCase && hasLowerCase) strength += 25;
            if (hasNumbers) strength += 25;
            
            // Determinar texto y color
            let text = '';
            let color = '';
            
            if (strength < 50) {
                text = 'Débil';
                color = '#e74c3c';
            } else if (strength < 75) {
                text = 'Media';
                color = '#f39c12';
            } else {
                text = 'Fuerte';
                color = '#27ae60';
            }
            
            // Aplicar cambios
            strengthBar.style.width = strength + '%';
            strengthBar.style.backgroundColor = color;
            strengthText.textContent = text;
            strengthText.style.color = color;
        }
        
        // Verificar si las contraseñas coinciden
        function checkPasswordMatch() {
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirm_password').value;
            const matchElement = document.getElementById('passwordMatch');
            
            if (!confirmPassword) {
                matchElement.textContent = '';
                return;
            }
            
            if (password === confirmPassword) {
                matchElement.innerHTML = '<i class="fas fa-check"></i> Las contraseñas coinciden';
                matchElement.style.color = '#27ae60';
            } else {
                matchElement.innerHTML = '<i class="fas fa-times"></i> Las contraseñas no coinciden';
                matchElement.style.color = '#e74c3c';
            }
        }
        
        // Actualizar indicador de regla
        function updateRule(ruleId, isValid) {
            const rule = document.getElementById(ruleId);
            if (rule) {
                if (isValid) {
                    rule.classList.remove('invalid');
                    rule.classList.add('valid');
                    rule.querySelector('i').className = 'fas fa-check';
                } else {
                    rule.classList.remove('valid');
                    rule.classList.add('invalid');
                    rule.querySelector('i').className = 'fas fa-times';
                }
            }
        }
        
        // Resetear todas las reglas
        function resetRules() {
            updateRule('ruleLength', false);
            updateRule('ruleUpper', false);
            updateRule('ruleLower', false);
            updateRule('ruleNumber', false);
        }
