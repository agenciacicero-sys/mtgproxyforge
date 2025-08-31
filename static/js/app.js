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
                                ${card.editions.map(edition => {
                                    const portugueseIndicator = edition.has_portuguese ? '🇵🇹 ' : '';
                                    return `
                                        <option value="${edition.set}" ${edition.set === card.set_code ? 'selected' : ''}>
                                            ${portugueseIndicator}${edition.set_name} (${edition.set.toUpperCase()})
                                        </option>
                                    `;
                                }).join('')}
                            </select>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;

        return col;
    }

    async changeLanguage(cardIndex, langCode) {
        console.log(`Changing language for card ${cardIndex} to ${langCode}`);
        await this.updateCardByFilters(cardIndex, langCode, null);
    }

    async changeEdition(cardIndex, setCode) {
        console.log(`Changing edition for card ${cardIndex} to ${setCode}`);
        const card = this.processedCards[cardIndex];
        const currentLang = card.lang || 'en';
        await this.updateCardByFilters(cardIndex, currentLang, setCode);
    }

    async updateCardByFilters(cardIndex, langCode, setCode) {
        const card = this.processedCards[cardIndex];
        if (!card) {
            console.error('Card not found at index:', cardIndex);
            return;
        }

        const cardElement = document.querySelector(`[data-card-index="${cardIndex}"]`);
        if (!cardElement) {
            console.error('Card element not found for index:', cardIndex);
            return;
        }

        const imgElement = cardElement.querySelector('img');
        const placeholderElement = cardElement.querySelector('.placeholder-img');

        // Show loading state
        cardElement.classList.add('image-loading');

        try {
            const requestBody = { 
                cardName: card.original_name || card.name,
                setCode: setCode,
                langCode: langCode
            };
            
            console.log('Sending request with:', requestBody);

            const response = await fetch('/api/get-card-by-lang-and-set', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody)
            });

            console.log('Response status:', response.status);
            const data = await response.json();
            console.log('Response data:', data);

            if (response.ok && data.card) {
                // Update card data in the array
                const updatedCard = {
                    ...card,
                    name: data.card.name || data.card.printed_name || card.name,
                    image_url: data.card.image_url,
                    scryfall_id: data.card.scryfall_id || data.card.id,
                    set_code: data.card.set_code || data.card.set,
                    set_name: data.card.set_name,
                    lang: data.card.lang,
                    lang_name: data.card.lang_name,
                    editions: card.editions, // Keep original editions list
                    languages: card.languages // Keep original languages list
                };
                
                this.processedCards[cardIndex] = updatedCard;

                // Update image with error handling
                if (data.card.image_url) {
                    if (imgElement) {
                        imgElement.onerror = function() {
                            this.style.display = 'none';
                            if (placeholderElement) placeholderElement.style.display = 'flex';
                        };
                        imgElement.onload = function() {
                            this.style.display = 'block';
                            if (placeholderElement) placeholderElement.style.display = 'none';
                        };
                        imgElement.src = data.card.image_url;
                    }
                } else {
                    // No image available
                    if (imgElement) imgElement.style.display = 'none';
                    if (placeholderElement) placeholderElement.style.display = 'flex';
                }

                // Update card title
                const cardTitleElement = cardElement.querySelector('.card-title');
                if (cardTitleElement) {
                    const cardDisplayName = data.card.name || data.card.printed_name || card.name;
                    cardTitleElement.textContent = cardDisplayName;
                    cardTitleElement.title = cardDisplayName;
                    
                    // Update set information
                    const setNameElement = cardElement.querySelector('.card-text.small');
                    if (setNameElement) {
                        setNameElement.textContent = data.card.set_name || `${data.card.set_code || data.card.set || 'Unknown'} Set`;
                    }

                    // Update dropdowns to reflect current selection and available options
                    this.updateDropdowns(cardIndex, data.card);
                    this.updateLanguageOptions(cardIndex, data.available_languages);

                    console.log(`Card updated: ${cardDisplayName} (${data.card.lang || 'en'}) - ${data.card.set_name}`);
                }

            } else {
                const errorMsg = data.error || 'Carta não encontrada com os filtros especificados';
                console.error('API response error:', data);
                console.error('Error message:', errorMsg);
                this.showError(`Erro ao carregar carta: ${errorMsg}`);
            }

        } catch (error) {
            console.error('Error updating card - full error:', error);
            console.error('Error message:', error.message);
            console.error('Error stack:', error.stack);
            this.showError(`Erro ao carregar nova versão da carta: ${error.message}`);
        } finally {
            cardElement.classList.remove('image-loading');
        }
    }

    checkPortugueseAvailability(editions, setCode) {
        // Check if there's any Portuguese version available for this set
        return editions.some(edition => 
            edition.set === setCode && edition.lang === 'pt'
        );
    }

    updateDropdowns(cardIndex, cardData) {
        const cardElement = document.querySelector(`[data-card-index="${cardIndex}"]`);
        if (!cardElement) return;
        
        // Update language selector
        const langSelector = cardElement.querySelector('.language-selector');
        if (langSelector && cardData.lang) {
            langSelector.value = cardData.lang;
            console.log(`Updated language selector to: ${cardData.lang}`);
        }

        // Update edition selector
        const editionSelector = cardElement.querySelector('.edition-selector');
        if (editionSelector && (cardData.set || cardData.set_code)) {
            const setCode = cardData.set || cardData.set_code;
            editionSelector.value = setCode;
            console.log(`Updated edition selector to: ${setCode}`);
        }
    }

    updateLanguageOptions(cardIndex, availableLanguages) {
        const cardElement = document.querySelector(`[data-card-index="${cardIndex}"]`);
        if (!cardElement) return;
        
        const langSelector = cardElement.querySelector('.language-selector');
        if (!langSelector || !availableLanguages) return;
        
        const currentValue = langSelector.value;
        
        // Update options
        langSelector.innerHTML = availableLanguages.map(language => `
            <option value="${language.code}" ${language.code === currentValue ? 'selected' : ''}>
                ${language.name}
            </option>
        `).join('');
        
        console.log(`Updated language options for card ${cardIndex}:`, availableLanguages);
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
