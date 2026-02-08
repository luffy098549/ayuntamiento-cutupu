
document.addEventListener('DOMContentLoaded', function() {
    const preloader = document.getElementById('preloader');
    const body = document.body;
    
    // Agregar clase de animación al contenido principal
    const mainContent = document.querySelector('main.container');
    if (mainContent) {
        mainContent.classList.add('content-animate');
    }
    
    // Simular tiempo de carga (puedes ajustar esto)
    setTimeout(function() {
        // Ocultar preloader
        preloader.classList.add('fade-out');
        
        // Después de la animación, remover completamente el preloader
        setTimeout(function() {
            preloader.style.display = 'none';
            
            // Activar animaciones para las tarjetas de servicios
            const serviceCards = document.querySelectorAll('.servicio-card');
            serviceCards.forEach((card, index) => {
                card.style.animationDelay = `${index * 0.1}s`;
                card.style.animationPlayState = 'running';
            });
            
        }, 500); // Tiempo para que termine la transición
        
    }, 1500); // Tiempo mínimo que se muestra el preloader
    
    // Si la página ya está cargada, ocultar más rápido
    window.addEventListener('load', function() {
        setTimeout(function() {
            if (!preloader.classList.contains('fade-out')) {
                preloader.classList.add('fade-out');
                setTimeout(function() {
                    preloader.style.display = 'none';
                }, 500);
            }
        }, 300);
    });
    
    // Animación suave para enlaces
    document.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', function(e) {
            if (this.getAttribute('href') && this.getAttribute('href').startsWith('#')) {
                e.preventDefault();
                const targetId = this.getAttribute('href');
                const targetElement = document.querySelector(targetId);
                
                if (targetElement) {
                    window.scrollTo({
                        top: targetElement.offsetTop - 100,
                        behavior: 'smooth'
                    });
                }
            }
        });
    });
    
    // Animación para el header al hacer scroll
    window.addEventListener('scroll', function() {
        const header = document.querySelector('.header');
        if (window.scrollY > 50) {
            header.style.transition = 'all 0.3s ease';
            header.style.boxShadow = '0 5px 15px rgba(0, 0, 0, 0.1)';
        } else {
            header.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.1)';
        }
    });
    
    // Efecto de hover mejorado para botones
    document.querySelectorAll('.btn-servicio, .btn-info').forEach(button => {
        button.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-3px) scale(1.02)';
        });
        
        button.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
    
    // Animación para la sección de información importante
    const infoSection = document.getElementById('info-ciudadania');
    if (infoSection) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.animation = 'fadeInUp 0.8s ease-out forwards';
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1 });
        
        observer.observe(infoSection);
    }
});

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
