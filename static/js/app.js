// MTG Proxy Forge - Frontend JavaScript
class MTGProxyForge {
    constructor() {
        this.processedCards = [];
        this.isProcessing = false;
        this.init();
    }

    init() {
        this.bindEvents();
        console.log('MTG Proxy Forge initialized');
    }

    bindEvents() {
        // Main process button
        document.getElementById('processListBtn').addEventListener('click', () => {
            this.processCardList();
        });

        // PDF generation button
        document.getElementById('generatePdfBtn').addEventListener('click', () => {
            this.generatePDF();
        });

        // Bulk action buttons
        document.getElementById('useLatestBtn').addEventListener('click', () => {
            this.useLatestEditions();
        });

        document.getElementById('useOriginalBtn').addEventListener('click', () => {
            this.useOriginalEditions();
        });

        // Search functionality
        document.getElementById('searchCards').addEventListener('input', (e) => {
            this.filterCards(e.target.value);
        });

        // Back to input button
        document.getElementById('backToInputBtn').addEventListener('click', () => {
            this.backToInput();
        });

        // Allow Enter key to process list
        document.getElementById('cardListInput').addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                this.processCardList();
            }
        });
    }

    async processCardList() {
        if (this.isProcessing) return;

        const cardListText = document.getElementById('cardListInput').value.trim();
        
        if (!cardListText) {
            this.showError('Por favor, cole uma lista de cartas válida.');
            return;
        }

        this.isProcessing = true;
        this.showSection('loading');
        this.updateProgress(0, 'Iniciando processamento...');

        try {
            const response = await fetch('/api/process-list', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ cardList: cardListText })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Erro ao processar lista');
            }

            this.processedCards = data.cards;
            this.displayCards(data.cards);
            this.updateSummary(data.total_cards, data.estimated_pages);
            this.showSection('review');
            this.showSuccess('Lista processada com sucesso!');

        } catch (error) {
            console.error('Error processing list:', error);
            this.showError(`Erro ao processar lista: ${error.message}`);
            this.showSection('input');
        } finally {
            this.isProcessing = false;
        }
    }

    displayCards(cards) {
        const cardsGrid = document.getElementById('cardsGrid');
        cardsGrid.innerHTML = '';

        cards.forEach((card, index) => {
            const cardElement = this.createCardElement(card, index);
            cardsGrid.appendChild(cardElement);
        });

        // Add smooth reveal animation
        setTimeout(() => {
            document.querySelectorAll('.card-preview').forEach((el, i) => {
                setTimeout(() => {
                    el.classList.add('show');
                }, i * 100);
            });
        }, 100);
    }

    createCardElement(card, index) {
        const col = document.createElement('div');
        col.className = 'col-lg-3 col-md-4 col-sm-6';

        const hasError = card.error;
        const errorClass = hasError ? 'card-error' : '';

        col.innerHTML = `
            <div class="card card-preview section-transition ${errorClass}" data-card-index="${index}">
                <div class="position-relative">
                    ${card.image_url ? 
                        `<img src="${card.image_url}" class="card-img-top" alt="${card.name}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">
                         <div class="placeholder-img" style="display: none;">
                             <i class="fas fa-image fa-2x"></i>
                         </div>` :
                        `<div class="placeholder-img">
                             <div class="text-center">
                                 <i class="fas fa-${hasError ? 'exclamation-triangle' : 'image'} fa-2x mb-2"></i>
                                 <div class="small">${hasError ? card.error : 'Sem imagem'}</div>
                             </div>
                         </div>`
                    }
                    <span class="quantity-badge">${card.quantity}x</span>
                </div>
                <div class="card-body">
                    <h6 class="card-title text-truncate" title="${card.name}">
                        ${card.name}
                    </h6>
                    <p class="card-text small text-muted mb-2">
                        ${card.set_name || card.set_code || 'Conjunto desconhecido'}
                    </p>
                    ${!hasError && card.languages && card.languages.length > 0 ? `
                        <div class="mb-2">
                            <label class="form-label small text-muted">Idioma:</label>
                            <select class="form-select form-select-sm language-selector" onchange="app.changeLanguage(${index}, this.value)">
                                ${card.languages.map(language => `
                                    <option value="${language.code}" ${language.code === card.lang ? 'selected' : ''}>
                                        ${language.name}
                                    </option>
                                `).join('')}
                            </select>
                        </div>
                    ` : ''}
                    ${!hasError && card.editions && card.editions.length > 0 ? `
                        <div class="mb-2">
                            <label class="form-label small text-muted">Edição:</label>
                            <select class="form-select form-select-sm edition-selector" onchange="app.changeEdition(${index}, this.value)">
                                ${card.editions.map(edition => `
                                    <option value="${edition.set}" ${edition.set === card.set_code ? 'selected' : ''}>
                                        ${edition.set_name} (${edition.set.toUpperCase()})
                                    </option>
                                `).join('')}
                            </select>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;

        return col;
    }

    async changeLanguage(cardIndex, langCode) {
        await this.updateCardByFilters(cardIndex, langCode, null);
    }

    async changeEdition(cardIndex, setCode) {
        const card = this.processedCards[cardIndex];
        const currentLang = card.lang || 'en';
        await this.updateCardByFilters(cardIndex, currentLang, setCode);
    }

    async updateCardByFilters(cardIndex, langCode, setCode) {
        const card = this.processedCards[cardIndex];
        if (!card) return;

        const cardElement = document.querySelector(`[data-card-index="${cardIndex}"]`);
        const imgElement = cardElement.querySelector('img');
        const placeholderElement = cardElement.querySelector('.placeholder-img');

        // Show loading state
        cardElement.classList.add('image-loading');

        try {
            const response = await fetch('/api/get-card-by-lang-and-set', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    cardName: card.original_name,
                    setCode: setCode,
                    langCode: langCode
                })
            });

            const data = await response.json();

            if (response.ok && data.card) {
                // Update card data
                this.processedCards[cardIndex] = {
                    ...card,
                    ...data.card,
                    editions: card.editions, // Keep original editions list
                    languages: card.languages // Keep original languages list
                };

                // Update image
                if (imgElement && data.card.image_url) {
                    imgElement.src = data.card.image_url;
                    imgElement.style.display = 'block';
                    if (placeholderElement) placeholderElement.style.display = 'none';
                }

                // Update set name and card name
                const setNameElement = cardElement.querySelector('.card-text.small');
                if (setNameElement) {
                    setNameElement.textContent = data.card.set_name || data.card.set || 'Conjunto desconhecido';
                }

                const cardTitleElement = cardElement.querySelector('.card-title');
                if (cardTitleElement) {
                    cardTitleElement.textContent = data.card.name;
                    cardTitleElement.title = data.card.name;
                }

                // Update dropdowns to reflect current selection
                this.updateDropdowns(cardIndex, data.card);

            } else {
                this.showError(`Erro ao carregar carta: ${data.error || 'Não encontrada'}`);
            }

        } catch (error) {
            console.error('Error updating card:', error);
            this.showError('Erro ao carregar nova versão da carta');
        } finally {
            cardElement.classList.remove('image-loading');
        }
    }

    updateDropdowns(cardIndex, cardData) {
        const cardElement = document.querySelector(`[data-card-index="${cardIndex}"]`);
        
        // Update language selector
        const langSelector = cardElement.querySelector('.language-selector');
        if (langSelector) {
            langSelector.value = cardData.lang || 'en';
        }

        // Update edition selector
        const editionSelector = cardElement.querySelector('.edition-selector');
        if (editionSelector) {
            editionSelector.value = cardData.set || '';
        }
    }

    useLatestEditions() {
        this.processedCards.forEach((card, index) => {
            if (card.editions && card.editions.length > 0) {
                const latestEdition = card.editions[0]; // Already sorted by release date
                const selector = document.querySelector(`[data-card-index="${index}"] .edition-selector`);
                if (selector) {
                    selector.value = latestEdition.set;
                    this.changeEdition(index, latestEdition.set);
                }
            }
        });
        this.showSuccess('Edições mais recentes aplicadas!');
    }

    useOriginalEditions() {
        // Try to restore original editions from the parsed list
        this.processedCards.forEach((card, index) => {
            if (card.editions && card.editions.length > 0) {
                // Find original edition or use first available
                const originalEdition = card.editions.find(ed => 
                    ed.set.toLowerCase() === (card.set_code || '').toLowerCase()
                ) || card.editions[0];
                
                const selector = document.querySelector(`[data-card-index="${index}"] .edition-selector`);
                if (selector) {
                    selector.value = originalEdition.set;
                    this.changeEdition(index, originalEdition.set);
                }
            }
        });
        this.showSuccess('Edições originais restauradas!');
    }

    filterCards(searchTerm) {
        const cardElements = document.querySelectorAll('.card-preview');
        const term = searchTerm.toLowerCase();

        cardElements.forEach(element => {
            const cardTitle = element.querySelector('.card-title').textContent.toLowerCase();
            const cardSet = element.querySelector('.card-text.small').textContent.toLowerCase();
            
            if (cardTitle.includes(term) || cardSet.includes(term)) {
                element.closest('.col-lg-3').style.display = 'block';
            } else {
                element.closest('.col-lg-3').style.display = 'none';
            }
        });
    }

    async generatePDF() {
        if (!this.processedCards.length) {
            this.showError('Nenhuma carta para gerar PDF');
            return;
        }

        // Get PDF configuration
        const config = {
            dpi: document.querySelector('input[name="dpi"]:checked').value,
            cutting_lines: document.getElementById('cuttingLines').checked,
            corner_guides: document.getElementById('cornerGuides').checked
        };

        this.showSection('pdf-loading');

        try {
            const response = await fetch('/api/generate-pdf', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    cards: this.processedCards,
                    config: config
                })
            });

            if (response.ok) {
                // Download the PDF
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'mtg_proxy_cards.pdf';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);

                this.showSection('review');
                this.showSuccess('PDF gerado e baixado com sucesso!');
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Erro ao gerar PDF');
            }

        } catch (error) {
            console.error('Error generating PDF:', error);
            this.showError(`Erro ao gerar PDF: ${error.message}`);
            this.showSection('review');
        }
    }

    updateSummary(totalCards, estimatedPages) {
        document.getElementById('totalCards').textContent = totalCards;
        document.getElementById('estimatedPages').textContent = estimatedPages;
    }

    updateProgress(percent, text) {
        const progressBar = document.getElementById('progressBar');
        const progressText = document.getElementById('progressText');
        
        if (progressBar) progressBar.style.width = `${percent}%`;
        if (progressText) progressText.textContent = text;
    }

    showSection(sectionName) {
        // Hide all sections
        const sections = ['input', 'loading', 'review', 'pdf-loading'];
        sections.forEach(section => {
            const element = document.getElementById(`${section}-section`);
            if (element) {
                element.classList.add('d-none');
                element.classList.remove('show');
            }
        });

        // Show target section
        const targetSection = document.getElementById(`${sectionName}-section`);
        if (targetSection) {
            targetSection.classList.remove('d-none');
            setTimeout(() => {
                targetSection.classList.add('show');
            }, 50);
        }
    }

    showError(message) {
        const errorAlert = document.getElementById('errorAlert');
        const errorMessage = document.getElementById('errorMessage');
        
        errorMessage.textContent = message;
        errorAlert.classList.remove('d-none');
        errorAlert.classList.add('show');
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            errorAlert.classList.remove('show');
            setTimeout(() => {
                errorAlert.classList.add('d-none');
            }, 300);
        }, 5000);
    }

    showSuccess(message) {
        const successAlert = document.getElementById('successAlert');
        const successMessage = document.getElementById('successMessage');
        
        successMessage.textContent = message;
        successAlert.classList.remove('d-none');
        successAlert.classList.add('show');
        
        // Auto-hide after 3 seconds
        setTimeout(() => {
            successAlert.classList.remove('show');
            setTimeout(() => {
                successAlert.classList.add('d-none');
            }, 300);
        }, 3000);
    }

    backToInput() {
        // Clear processed cards
        this.processedCards = [];
        
        // Clear the input textarea (optional - user might want to edit)
        // document.getElementById('cardListInput').value = '';
        
        // Clear search field
        const searchField = document.getElementById('searchCards');
        if (searchField) searchField.value = '';
        
        // Reset to input section
        this.showSection('input');
        
        // Show success message
        this.showSuccess('Pronto para nova lista de cartas!');
    }
}

// Initialize the application
const app = new MTGProxyForge();

// Make globally available for inline event handlers
window.app = app;

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'g') {
        e.preventDefault();
        const generateBtn = document.getElementById('generatePdfBtn');
        if (generateBtn && !generateBtn.disabled) {
            generateBtn.click();
        }
    }
});

console.log('MTG Proxy Forge frontend loaded successfully');
