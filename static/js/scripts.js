
        // Menú móvil
        document.addEventListener('DOMContentLoaded', function() {
            const btnMenu = document.querySelector('.btn-menu-movil');
            const navPrincipal = document.querySelector('.nav-principal');
            
            if (btnMenu) {
                btnMenu.addEventListener('click', function() {
                    this.classList.toggle('activo');
                    navPrincipal.classList.toggle('activo');
                    const expanded = this.getAttribute('aria-expanded') === 'true';
                    this.setAttribute('aria-expanded', !expanded);
                });
            }

            // Cerrar menú al hacer click en un enlace
            const navEnlaces = document.querySelectorAll('.nav-enlace');
            navEnlaces.forEach(enlace => {
                enlace.addEventListener('click', function() {
                    if (window.innerWidth <= 768) {
                        btnMenu.classList.remove('activo');
                        navPrincipal.classList.remove('activo');
                        btnMenu.setAttribute('aria-expanded', 'false');
                    }
                });
            });

            // Efecto scroll en header
            const header = document.querySelector('.header');
            let lastScroll = 0;

            window.addEventListener('scroll', function() {
                const currentScroll = window.pageYOffset;
                
                if (currentScroll > 100) {
                    header.classList.add('scrolled');
                } else {
                    header.classList.remove('scrolled');
                }
                
                lastScroll = currentScroll;
            });

            // Botón flotante para móvil
            const btnFlotante = document.querySelector('.btn-flotante-movil');
            if (btnFlotante) {
                window.addEventListener('scroll', function() {
                    if (window.pageYOffset > 300) {
                        btnFlotante.classList.add('visible');
                    } else {
                        btnFlotante.classList.remove('visible');
                    }
                });
            }

            // Actualizar año en footer
            const anioActual = document.getElementById('anio-actual');
            if (anioActual && !anioActual.textContent) {
                anioActual.textContent = new Date().getFullYear();
            }
        });
  


     
    // Mostrar alerta solo una vez
    if (!sessionStorage.getItem("alertMostrada")) {
        alert("Esta página fue hecha con fines educativos");
        sessionStorage.setItem("alertMostrada", "true");
    }

    // Control de scroll para header
    let lastScrollTop = 0;
    const header = document.querySelector('.header');

    window.addEventListener('scroll', () => {
        let scrollTop = window.pageYOffset || document.documentElement.scrollTop;

        if (scrollTop > lastScrollTop && scrollTop > 100) {
            // Bajando → ocultar header
            header.classList.add('oculto');
        } else {
            // Subiendo → mostrar header
            header.classList.remove('oculto');
        }

        lastScrollTop = scrollTop <= 0 ? 0 : scrollTop;
    });

    // Dropdown del perfil
    document.addEventListener('DOMContentLoaded', function() {
        const dropdownBtn = document.querySelector('.btn-perfil');
        const dropdownMenu = document.querySelector('.dropdown-menu');
        
        if (dropdownBtn && dropdownMenu) {
            dropdownBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                const isExpanded = this.getAttribute('aria-expanded') === 'true';
                this.setAttribute('aria-expanded', !isExpanded);
                dropdownMenu.style.display = isExpanded ? 'none' : 'block';
            });
            
            // Cerrar dropdown al hacer clic fuera
            document.addEventListener('click', function(e) {
                if (!dropdownBtn.contains(e.target) && !dropdownMenu.contains(e.target)) {
                    dropdownBtn.setAttribute('aria-expanded', 'false');
                    dropdownMenu.style.display = 'none';
                }
            });
        }
        
        // Menú móvil
        const menuBtn = document.querySelector('.btn-menu-movil');
        const menuPrincipal = document.querySelector('.nav-lista');
        
        if (menuBtn && menuPrincipal) {
            menuBtn.addEventListener('click', function() {
                const isExpanded = this.getAttribute('aria-expanded') === 'true';
                this.setAttribute('aria-expanded', !isExpanded);
                menuPrincipal.classList.toggle('mostrar');
            });
            
            // Cerrar menú al hacer clic en un enlace (para móviles)
            menuPrincipal.querySelectorAll('.nav-enlace').forEach(enlace => {
                enlace.addEventListener('click', function() {
                    menuPrincipal.classList.remove('mostrar');
                    menuBtn.setAttribute('aria-expanded', 'false');
                });
            });
        }
        
        // Actualizar año en el footer
        const yearSpan = document.getElementById('anio-actual');
        if (yearSpan && !yearSpan.textContent.trim()) {
            yearSpan.textContent = new Date().getFullYear();
        }
    });
