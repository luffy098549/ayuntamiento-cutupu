       // Navegación entre secciones del perfil
        document.querySelectorAll('.menu-item[data-target]').forEach(item => {
            item.addEventListener('click', function(e) {
                e.preventDefault();
                const targetId = this.getAttribute('data-target');
                
                // Actualizar menú activo
                document.querySelectorAll('.menu-item').forEach(i => i.classList.remove('activo'));
                this.classList.add('activo');
                
                // Mostrar sección correspondiente
                document.querySelectorAll('.perfil-seccion').forEach(sec => {
                    sec.classList.remove('activa');
                });
                document.getElementById(targetId).classList.add('activa');
            });
        });

        // Manejo de archivos para foto
        document.getElementById('file-input')?.addEventListener('change', function(e) {
            if (this.files && this.files[0]) {
                // En una implementación real, aquí subirías la imagen
                alert('Funcionalidad de subir foto en desarrollo. Por ahora usa tu nombre como avatar.');
                this.value = '';
            }
        });

        // Filtros en mis trámites
        document.querySelectorAll('.filtro-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                document.querySelectorAll('.filtro-btn').forEach(b => b.classList.remove('activo'));
                this.classList.add('activo');
            });
        });

        // Dropdown del perfil
        const dropdownBtn = document.querySelector('.btn-perfil');
        const dropdownMenu = document.querySelector('.dropdown-menu');
        
        if (dropdownBtn && dropdownMenu) {
            dropdownBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                const isExpanded = this.getAttribute('aria-expanded') === 'true';
                this.setAttribute('aria-expanded', !isExpanded);
                dropdownMenu.style.display = isExpanded ? 'none' : 'block';
            });
            
            document.addEventListener('click', function(e) {
                if (!dropdownBtn.contains(e.target) && !dropdownMenu.contains(e.target)) {
                    dropdownBtn.setAttribute('aria-expanded', 'false');
                    dropdownMenu.style.display = 'none';
                }
            });
        }
  