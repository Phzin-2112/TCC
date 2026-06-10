let currentSlide = 0;

function moveSlide(step) {
    const slides = document.querySelectorAll('.carousel-slide');
    const totalSlides = slides.length;
    // Atualiza o índice do slide atual com o valor de step
    currentSlide = (currentSlide + step + totalSlides) % totalSlides;
    const carousel = document.querySelector('.carousel');
    // Movendo o carousel com base no índice atual
    carousel.style.transform = `translateX(-${currentSlide * 100}%)`;
}

// Função para rodar o carousel automaticamente
function autoMoveSlide() {
    moveSlide(1); // Move para o próximo slide
}

// Inicializa a rotação automática a cada 3 segundos (3000ms)
setInterval(autoMoveSlide, 3000); // 3 segundos de intervalo

// Ajuste para garantir que o carousel funcione ao clicar nos botões de navegação
document.querySelector('.prev').addEventListener('click', () => moveSlide(-1));
document.querySelector('.next').addEventListener('click', () => moveSlide(1));

document.addEventListener('DOMContentLoaded', () => {
    const alerts = document.querySelectorAll('.flash-messages .alert');
    alerts.forEach((alert) => {
        // Adiciona a classe show para animação
        alert.classList.add('show');

        // Remove após 2 segundos (2000ms)
        setTimeout(() => {
            alert.classList.remove('show');
            // Remove do DOM após a animação (0.5s)
            setTimeout(() => alert.remove(), 500);
        }, 2000);
    });
});

document.querySelector('#btn').addEventListener('click', () => {
  window.location.href = 'login.html';
});



/*    const form = document.querySelector('#contato-form form');

     form.addEventListener('submit', function(e){
        e.preventDefault(); // previne o reload da página

        // pega os valores do formulário
        const nome = document.getElementById('nome').value;
        const email = document.getElementById('email').value;
        const telefone = document.getElementById('telefone').value;
        const mensagem = document.getElementById('mensagem').value;
        // cria objeto JSON
        const dados = {
            nome: nome,
            email: email,
            telefone: telefone,
            mensagem: mensagem,
             data: new Date().toISOString()
         };

        // pega contatos existentes do localStorage
        let contatos = JSON.parse(localStorage.getItem('contatos') || '[]');
         // adiciona novo contato
         contatos.push(dados);
         // salva de volta no localStorage
         localStorage.setItem('contatos', JSON.stringify(contatos));
         alert('Mensagem enviada com sucesso!');
         // limpa o formulário
        form.reset();
});


console.log('Dados: ' + localStorage.getItem('contatos'))
    console.log('Contatos salvos:', JSON.parse(localStorage.getItem('contatos') || '[]')); */


    