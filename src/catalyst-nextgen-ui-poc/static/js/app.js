        function appData() {
            return {
                currentView: 'workflow',
                viewMode: 'landing',  // 'landing' or 'workspace'
                showConfigModal: false,
                docUploaded: false,
                docInfo: 'No document uploaded',
                transformations: [],
                selectedTransform: '',
                processing: false,
                steps: [],
                stepOutputs: [],
                currentViewingStep: 0,
                currentStreamingStep: null,
                userSelectedStep: false,
                downloadUrl: '',
                turndownService: null,
                editingTransform: false,
                addingTransform: false,
                editData: { steps: [], options: {} },
                // Canvas type system
                canvasTypes: {},
                currentCanvasType: 'text_editor',
                uploadedFileType: '',
                defaultCanvasType: 'text_editor',
                taskOptions: {},
                directionOptions: {},
                selectedOptions: {},
                uploadedFiles: [],
                labeledFiles: {},  // For tasks with labeled file inputs
                excelColumnHeaders: [],
                leftPanelCollapsed: false,
                rightPanelCollapsed: false,
                alignmentData: null,
                alignmentDataOriginal: null,
                alignmentEditMode: false,
                selectedOrphan1: null,
                selectedOrphan2: null,
                creatingMatch: false,
                // Chat interface state
                chatMessages: [],
                chatSessionId: null,
                userQuestion: '',
                isWaitingForChat: false,
                // Direction filtering
                taskSearch: '',
                landingSearch: '',
                selectedCategory: 'all',
                filteredTasks: [],
                landingFilteredTasks: [],
                lastSelectedTransform: null,
                
                // Workflow library filtering
                workflowSearch: '',
                filteredWorkflows: [],
                
                selectPairAndScroll(idx) {
                    // Set selected pair (always update, don't toggle off if clicking different pair)
                    this.selectedPair = idx;
                    
                    // If a pair is selected, scroll both columns to align the cards
                    if (this.selectedPair !== null) {
                        this.$nextTick(() => {
                            const leftEl = document.getElementById(`left-${idx}`);
                            const rightEl = document.getElementById(`right-${idx}`);
                            const leftContainer = document.getElementById('left-scroll-container');
                            const rightContainer = document.getElementById('right-scroll-container');
                            
                            if (leftEl && rightEl && leftContainer && rightContainer) {
                                // Calculate scroll positions to center the cards in view
                                const containerHeight = leftContainer.clientHeight;
                                const leftOffset = leftEl.offsetTop - (containerHeight / 2) + (leftEl.clientHeight / 2);
                                const rightOffset = rightEl.offsetTop - (containerHeight / 2) + (rightEl.clientHeight / 2);
                                
                                // Smooth scroll both containers
                                leftContainer.scrollTo({
                                    top: Math.max(0, leftOffset),
                                    behavior: 'smooth'
                                });
                                
                                rightContainer.scrollTo({
                                    top: Math.max(0, rightOffset),
                                    behavior: 'smooth'
                                });
                            }
                        });
                    }
                },
                
                toggleEditMode() {
                    this.alignmentEditMode = !this.alignmentEditMode;
                    if (!this.alignmentEditMode) {
                        // Clear selections when exiting edit mode
                        this.selectedPair = null;
                        this.selectedOrphan1 = null;
                        this.selectedOrphan2 = null;
                    }
                },
                
                handleCardClick(idx, pair, side) {
                    // In edit mode, handle orphan selection for linking
                    if (this.alignmentEditMode) {
                        if (pair.type === 'orphan_file1' && side === 'left') {
                            // Toggle selection of orphan from file 1
                            this.selectedOrphan1 = this.selectedOrphan1 === idx ? null : idx;
                            // Check if both orphans are selected
                            if (this.selectedOrphan1 !== null && this.selectedOrphan2 !== null) {
                                this.createMatch(this.selectedOrphan1, this.selectedOrphan2);
                            }
                            return;
                        } else if (pair.type === 'orphan_file2' && side === 'right') {
                            // Toggle selection of orphan from file 2
                            this.selectedOrphan2 = this.selectedOrphan2 === idx ? null : idx;
                            // Check if both orphans are selected
                            if (this.selectedOrphan1 !== null && this.selectedOrphan2 !== null) {
                                this.createMatch(this.selectedOrphan1, this.selectedOrphan2);
                            }
                            return;
                        }
                    }
                    
                    // Normal mode: select matched pair to view details
                    if (pair.type === 'match') {
                        this.selectPairAndScroll(idx);
                    }
                },
                
                unlinkMatch(pairIndex) {
                    if (!this.alignmentData) return;
                    
                    const pairs = this.alignmentData.unified_pairs || this.alignmentData.matched_pairs;
                    if (!pairs || !pairs[pairIndex]) return;
                    
                    const pair = pairs[pairIndex];
                    
                    // Only unlink if it's a matched pair
                    if (pair.type !== 'match') return;
                    
                    // Store file2 data before modifying
                    const file2Value = pair.file2_value;
                    const file2Index = pair.file2_index;
                    
                    // Convert matched pair to orphan_file1
                    pair.type = 'orphan_file1';
                    pair.file2_value = null;
                    pair.file2_index = null;
                    pair.similarity = 0;
                    pair.is_matched = false;
                    pair.diff = null;
                    pair.analysis = null;
                    
                    // Create orphan for file2
                    const orphan2 = {
                        type: 'orphan_file2',
                        file1_value: null,
                        file1_index: null,
                        file2_value: file2Value,
                        file2_index: file2Index,
                        similarity: 0,
                        is_matched: false
                    };
                    
                    // Insert orphan2 after current position
                    pairs.splice(pairIndex + 1, 0, orphan2);
                    
                    // Update stats
                    this.alignmentData.total_matches--;
                    this.alignmentData.total_orphans += 2;
                    
                    // Recalculate average similarity
                    const matchedPairs = pairs.filter(p => p.type === 'match');
                    if (matchedPairs.length > 0) {
                        const avgSim = matchedPairs.reduce((sum, p) => sum + p.similarity, 0) / matchedPairs.length;
                        this.alignmentData.avg_similarity = avgSim;
                    } else {
                        this.alignmentData.avg_similarity = 0;
                    }
                    
                    // Clear selection
                    this.selectedPair = null;
                    
                    // Force re-render
                    this.stepOutputs[this.currentViewingStep] = `ALIGNMENT_RESULT:${JSON.stringify(this.alignmentData)}`;
                },
                
                async createMatch(orphan1Index, orphan2Index) {
                    if (!this.alignmentData) return;
                    
                    const pairs = this.alignmentData.unified_pairs || this.alignmentData.matched_pairs;
                    if (!pairs) return;
                    
                    const orphan1 = pairs[orphan1Index];
                    const orphan2 = pairs[orphan2Index];
                    
                    // Validate that both are orphans
                    if (!orphan1 || !orphan2 || orphan1.type !== 'orphan_file1' || orphan2.type !== 'orphan_file2') {
                        console.error('Invalid orphan selection');
                        this.selectedOrphan1 = null;
                        this.selectedOrphan2 = null;
                        return;
                    }
                    
                    // Show loading indicator
                    this.creatingMatch = true;
                    
                    // Calculate similarity using backend
                    let similarity = 0.5;
                    try {
                        const response = await fetch('/api/calculate-similarity', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                text1: orphan1.file1_value,
                                text2: orphan2.file2_value
                            })
                        });
                        const result = await response.json();
                        if (result.success) {
                            similarity = result.similarity;
                        }
                    } catch (error) {
                        console.error('Error calculating similarity:', error);
                    }
                    
                    // Calculate diff if enabled
                    let diff = null;
                    if (this.alignmentData.include_diff) {
                        diff = this.calculateDiff(orphan1.file1_value, orphan2.file2_value);
                    }
                    
                    try {
                        // Convert orphan1 to a matched pair
                        orphan1.type = 'match';
                        orphan1.file2_value = orphan2.file2_value;
                        orphan1.file2_index = orphan2.file2_index;
                        orphan1.similarity = similarity;
                        orphan1.is_matched = true;
                        orphan1.manual = true;
                        
                        if (diff) {
                            orphan1.diff = diff;
                        }
                        
                        // Remove orphan2 from the list (it's now part of the match)
                        pairs.splice(orphan2Index, 1);
                        
                        // Update stats
                        this.alignmentData.total_matches++;
                        this.alignmentData.total_orphans -= 2;
                        
                        // Recalculate average similarity
                        const matchedPairs = pairs.filter(p => p.type === 'match');
                        if (matchedPairs.length > 0) {
                            const avgSim = matchedPairs.reduce((sum, p) => sum + p.similarity, 0) / matchedPairs.length;
                            this.alignmentData.avg_similarity = avgSim;
                        }
                        
                        // Clear selections
                        this.selectedOrphan1 = null;
                        this.selectedOrphan2 = null;
                        
                        // Force re-render
                        this.stepOutputs[this.currentViewingStep] = `ALIGNMENT_RESULT:${JSON.stringify(this.alignmentData)}`;
                    } finally {
                        // Always hide loading indicator
                        this.creatingMatch = false;
                    }
                },
                
                calculateDiff(text1, text2) {
                    // Simple word-level diff using JavaScript
                    const words1 = text1.split(/\s+/);
                    const words2 = text2.split(/\s+/);
                    
                    // Build a simple diff
                    const result = [];
                    const maxLen = Math.max(words1.length, words2.length);
                    
                    // Simple approach: compare word by word
                    let i = 0, j = 0;
                    while (i < words1.length || j < words2.length) {
                        if (i >= words1.length) {
                            // Only words2 left (added)
                            result.push(`<span class="diff-added">${words2[j]}</span>`);
                            j++;
                        } else if (j >= words2.length) {
                            // Only words1 left (removed)
                            result.push(`<span class="diff-removed">${words1[i]}</span>`);
                            i++;
                        } else if (words1[i] === words2[j]) {
                            // Same word
                            result.push(words1[i]);
                            i++;
                            j++;
                        } else {
                            // Different - check if next word matches
                            if (words1[i] === words2[j + 1]) {
                                // Word added in text2
                                result.push(`<span class="diff-added">${words2[j]}</span>`);
                                j++;
                            } else if (words1[i + 1] === words2[j]) {
                                // Word removed from text1
                                result.push(`<span class="diff-removed">${words1[i]}</span>`);
                                i++;
                            } else {
                                // Both different
                                result.push(`<span class="diff-removed">${words1[i]}</span>`);
                                result.push(`<span class="diff-added">${words2[j]}</span>`);
                                i++;
                                j++;
                            }
                        }
                    }
                    
                    return result.join(' ');
                },
                
                resetAlignment() {
                    if (!this.alignmentDataOriginal) return;
                    
                    // Show confirmation for better UX (Don Norman: provide feedback)
                    if (!confirm('Reset all changes to original alignment?')) return;
                    
                    // Restore from original
                    this.alignmentData = JSON.parse(JSON.stringify(this.alignmentDataOriginal));
                    this.selectedPair = null;
                    
                    // Update the step output to match
                    this.stepOutputs[this.currentViewingStep] = `ALIGNMENT_RESULT:${JSON.stringify(this.alignmentData)}`;
                },
                
                initializeChatSession() {
                    // Don't re-initialize if already initialized
                    if (this.chatSessionId) return;
                    
                    // Extract session ID from RAG_INITIALIZED output
                    const output = this.stepOutputs[this.currentViewingStep];
                    
                    if (output && output.startsWith('RAG_INITIALIZED:')) {
                        const jsonStr = output.replace('RAG_INITIALIZED:', '');
                        try {
                            const data = JSON.parse(jsonStr);
                            if (data.error) {
                                this.chatMessages = [{
                                    type: 'system',
                                    content: `❌ Error: ${data.error}`
                                }];
                                return;
                            }
                            this.chatSessionId = data.session_id;
                            if (data.document_count) {
                                this.chatMessages = [{
                                    type: 'system',
                                    content: `✅ Ready to chat! Indexed ${data.document_count} document(s) into ${data.chunk_count} searchable chunks.`
                                }];
                            }
                        } catch(e) {
                            this.chatMessages = [{
                                type: 'system',
                                content: '❌ Error: Failed to initialize chat session'
                            }];
                        }
                    }
                },
                
                async sendChatMessage() {
                    if (!this.userQuestion.trim() || !this.chatSessionId || this.isWaitingForChat) return;
                    
                    const question = this.userQuestion.trim();
                    this.userQuestion = '';
                    
                    // Add user message
                    this.chatMessages.push({
                        type: 'user',
                        content: question
                    });
                    
                    // Scroll to bottom
                    this.$nextTick(() => {
                        const container = document.getElementById('chat-messages-container');
                        if (container) container.scrollTop = container.scrollHeight;
                    });
                    
                    this.isWaitingForChat = true;
                    
                    try {
                        const response = await fetch('/api/chat', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                session_id: this.chatSessionId,
                                question: question
                            })
                        });
                        
                        const data = await response.json();
                        
                        if (data.error) {
                            this.chatMessages.push({
                                type: 'system',
                                content: '❌ Error: ' + data.error
                            });
                        } else {
                            this.chatMessages.push({
                                type: 'assistant',
                                content: data.answer,
                                sources: data.sources || []
                            });
                        }
                    } catch (error) {
                        this.chatMessages.push({
                            type: 'system',
                            content: '❌ Network error. Please try again.'
                        });
                    } finally {
                        this.isWaitingForChat = false;
                        
                        // Scroll to bottom
                        this.$nextTick(() => {
                            const container = document.getElementById('chat-messages-container');
                            if (container) container.scrollTop = container.scrollHeight;
                        });
                    }
                },
                
                get hasCanvasData() {
                    // Check if Canvas has any data/content
                    return this.stepOutputs.length > 0 || this.processing;
                },
                
                get leftPanelColSpan() {
                    // When Canvas is empty, give Project Setup more space (6 cols = 50%)
                    // When Canvas has data, use normal size (3 cols = 25%)
                    return this.hasCanvasData ? 'col-span-3' : 'col-span-6';
                },
                
                get canvasColSpan() {
                    const hasData = this.hasCanvasData;
                    
                    // When no data, Canvas is smaller to make room for expanded Project Setup
                    if (!hasData) {
                        if (this.leftPanelCollapsed && this.rightPanelCollapsed) return 10;
                        if (this.rightPanelCollapsed) return 5; // Left expanded (6) + Canvas (5) = 11, Right collapsed (1) = 12
                        if (this.leftPanelCollapsed) return 8;
                        return 3; // Left expanded (6) + Canvas (3) + Right expanded (3) = 12
                    }
                    
                    // When has data, use normal responsive sizing
                    if (this.leftPanelCollapsed && this.rightPanelCollapsed) return 10;
                    if (this.leftPanelCollapsed || this.rightPanelCollapsed) return 8;
                    return 6;
                },
                
                togglePanels() {
                    // Toggle both panels at once for focus mode
                    const bothCollapsed = this.leftPanelCollapsed && this.rightPanelCollapsed;
                    this.leftPanelCollapsed = !bothCollapsed;
                    this.rightPanelCollapsed = !bothCollapsed;
                },
                
                async init() {
                    // Keyboard shortcut: [ to toggle left, ] to toggle right, \ to toggle both
                    document.addEventListener('keydown', (e) => {
                        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) return;
                        
                        if (e.key === '[') {
                            this.leftPanelCollapsed = !this.leftPanelCollapsed;
                        } else if (e.key === ']') {
                            this.rightPanelCollapsed = !this.rightPanelCollapsed;
                        } else if (e.key === '\\') {
                            this.togglePanels();
                        }
                    });
                
                    // Initialize Turndown for HTML to Markdown conversion
                    this.turndownService = new TurndownService({
                        headingStyle: 'atx',
                        bulletListMarker: '-',
                        codeBlockStyle: 'fenced'
                    });
                    
                    await this.loadCanvasTypes();
                    await this.loadTransformations();
                },
                
                async loadCanvasTypes() {
                    try {
                        const response = await fetch('/api/canvas-types');
                        const data = await response.json();
                        this.canvasTypes = data.canvas_types || {};
                    } catch (error) {
                        console.error('Error loading canvas types:', error);
                    }
                },
                
                async loadTransformations() {
                    try {
                        const response = await fetch('/api/transformations');
                        const data = await response.json();
                        this.transformations = data.transformations || data;
                        this.filterTasks(); // Initialize filtered list
                        this.filterLandingTasks(); // Initialize landing page filtered list
                        this.filteredWorkflows = this.transformations; // Initialize workflow library view
                    } catch (error) {
                        console.error('Error loading transformations:', error);
                    }
                },
                
                filterWorkflows() {
                    if (!this.workflowSearch) {
                        this.filteredWorkflows = this.transformations;
                        return;
                    }
                    
                    const search = this.workflowSearch.toLowerCase();
                    this.filteredWorkflows = this.transformations.filter(t => 
                        t.name.toLowerCase().includes(search) ||
                        (t.description && t.description.toLowerCase().includes(search)) ||
                        t.key.toLowerCase().includes(search) ||
                        (t.category && t.category.toLowerCase().includes(search))
                    );
                },
                
                isBuiltInWorkflow(key) {
                    // Check if this is a built-in workflow (not user-created)
                    const builtInKeys = [
                        'chat_with_documents', 'fact_check_document', 'content_audit',
                        'align_excel', 'generate_podcast', 'tech_to_faq',
                        'executive_summary', 'simplify_language', 'anonymize',
                        'update_derivative_asset'
                    ];
                    return builtInKeys.includes(key);
                },
                
                filterTasks() {
                    let filtered = this.transformations;
                    
                    // Filter by search query
                    if (this.taskSearch) {
                        const search = this.taskSearch.toLowerCase();
                        filtered = filtered.filter(t => 
                            t.name.toLowerCase().includes(search) ||
                            t.description.toLowerCase().includes(search) ||
                            t.key.toLowerCase().includes(search)
                        );
                    }
                    
                    // Filter by category
                    if (this.selectedCategory !== 'all') {
                        filtered = filtered.filter(t => {
                            const category = (t.category || 'update').toLowerCase();
                            return category === this.selectedCategory;
                        });
                    }
                    
                    this.filteredTasks = filtered;
                },
                
                filterLandingTasks() {
                    let filtered = this.transformations;
                    
                    // Filter by search query (only triggered on Enter key)
                    if (this.landingSearch) {
                        const search = this.landingSearch.toLowerCase();
                        filtered = filtered.filter(t => 
                            t.name.toLowerCase().includes(search) ||
                            t.description.toLowerCase().includes(search) ||
                            t.key.toLowerCase().includes(search)
                        );
                    }
                    
                    // Filter by category
                    if (this.selectedCategory !== 'all') {
                        filtered = filtered.filter(t => {
                            const category = (t.category || 'update').toLowerCase();
                            return category === this.selectedCategory;
                        });
                    }
                    
                    this.landingFilteredTasks = filtered;
                },
                
                selectCategory(category) {
                    this.selectedCategory = category;
                    this.filterTasks();
                    this.filterLandingTasks();
                },
                
                handleLandingSearchKeydown(event) {
                    if (event.key === 'Enter') {
                        this.filterLandingTasks();
                    }
                },
                
                getTaskCategory(task) {
                    return (task.category || 'update').toLowerCase();
                },
                
                getTaskIcon(task) {
                    if (task.icon) {
                        return task.icon;
                    }
                    const category = this.getTaskCategory(task);
                    switch (category) {
                        case 'ask':
                            return '❓';
                        case 'analyze':
                            return '🔍';
                        case 'compare':
                            return '🔗';
                        case 'create':
                            return '🎨';
                        case 'update':
                            return '🛠️';
                        default:
                            return '📝';
                    }
                },
                
                async selectTask(key) {
                    this.selectedTransform = key;
                    this.updateCanvasType();
                    
                    // Clear old RAG sessions when switching to a new task
                    try {
                        await fetch('/api/session/reset', { method: 'POST' });
                    } catch (error) {
                        console.error('Error clearing RAG sessions:', error);
                    }
                    
                    // Clear files when switching tasks
                    this.uploadedFiles = [];
                    this.labeledFiles = {};
                    this.docUploaded = false;
                    
                    // Clear chat state when switching tasks
                    this.chatMessages = [];
                    this.chatSessionId = null;
                    this.userQuestion = '';
                    
                    // If on landing page, show config modal
                    if (this.viewMode === 'landing') {
                        this.showConfigModal = true;
                    }
                },
                
                startWorkflow() {
                    // Transition from landing to workspace
                    this.showConfigModal = false;
                    this.viewMode = 'workspace';
                    this.leftPanelCollapsed = true; // Start with setup panel collapsed
                    
                    // Auto-start the workflow if all requirements are met
                    this.$nextTick(() => {
                        if (this.canRunTask()) {
                            setTimeout(() => {
                                this.runDraft();
                            }, 300); // Small delay for smooth transition
                        }
                    });
                },
                
                reopenConfigModal() {
                    // Reopen the modal to edit configuration
                    this.showConfigModal = true;
                },
                
                closeConfigModal() {
                    this.showConfigModal = false;
                    this.selectedTransform = '';
                },
                
                get currentTaskRequiresDual() {
                    if (!this.selectedTransform) return false;
                    const task = this.transformations.find(t => t.key === this.selectedTransform);
                    return task ? (task.requires_dual_upload || false) : false;
                },
                
                get currentTaskAllowsMultiple() {
                    if (!this.selectedTransform) return false;
                    const task = this.transformations.find(t => t.key === this.selectedTransform);
                    return task ? (task.allow_multiple_files || false) : false;
                },
                
                get currentTaskFileTypes() {
                    if (!this.selectedTransform) return '.docx,.txt,.md';
                    const task = this.transformations.find(t => t.key === this.selectedTransform);
                    if (!task) return '.docx,.txt,.md';
                    return task.input_file_types.map(t => '.' + t).join(',');
                },
                
                get currentTaskFileHint() {
                    if (!this.selectedTransform) return 'Select a direction first';
                    const task = this.transformations.find(t => t.key === this.selectedTransform);
                    if (!task) return 'Upload your file';
                    const fileTypes = task.input_file_types.map(t => t.toUpperCase()).join(', ');
                    if (task.requires_dual_upload) {
                        return `Upload 2 ${fileTypes} files to compare`;
                    }
                    return `Upload 1 ${fileTypes} file`;
                },
                
                get filesMatchTask() {
                    // For labeled files, use separate validation
                    if (this.currentTaskUsesLabeledFiles) {
                        return this.allLabeledFilesUploaded;
                    }
                    
                    if (!this.selectedTransform || this.uploadedFiles.length === 0) return false;
                    const task = this.transformations.find(t => t.key === this.selectedTransform);
                    if (!task) return false;
                    
                    // Check file count matches requirement
                    const requiresDual = task.requires_dual_upload || false;
                    const allowsMultiple = task.allow_multiple_files || false;
                    
                    if (requiresDual && this.uploadedFiles.length !== 2) return false;
                    if (!requiresDual && !allowsMultiple && this.uploadedFiles.length !== 1) return false;
                    if (allowsMultiple && this.uploadedFiles.length === 0) return false;
                    
                    // Check file types match
                    const allowedTypes = task.input_file_types || ['docx'];
                    return this.uploadedFiles.every(f => allowedTypes.includes(f.type));
                },
                
                // Labeled file input support
                get currentTaskUsesLabeledFiles() {
                    if (!this.selectedTransform) return false;
                    const task = this.transformations.find(t => t.key === this.selectedTransform);
                    return task ? (task.requires_labeled_files || false) : false;
                },
                
                get currentTaskLabeledInputs() {
                    if (!this.selectedTransform) return [];
                    const task = this.transformations.find(t => t.key === this.selectedTransform);
                    return task ? (task.labeled_file_inputs || []) : [];
                },
                
                get allLabeledFilesUploaded() {
                    // If workflow doesn't use labeled files, return false
                    if (!this.currentTaskUsesLabeledFiles) {
                        return false;
                    }
                    const requiredInputs = this.currentTaskLabeledInputs.filter(input => input.required);
                    // If there are no required inputs, return false (empty array .every() returns true)
                    if (requiredInputs.length === 0) {
                        return false;
                    }
                    return requiredInputs.every(input => this.labeledFiles[input.key]);
                },
                
                get labeledFilesStatusText() {
                    const total = this.currentTaskLabeledInputs.filter(input => input.required).length;
                    const uploaded = Object.keys(this.labeledFiles).length;
                    
                    if (uploaded === total) {
                        return `All ${total} files uploaded ✓`;
                    } else {
                        return `${uploaded} of ${total} files uploaded`;
                    }
                },
                
                get filesMismatchMessage() {
                    if (!this.selectedTransform || this.uploadedFiles.length === 0) return '';
                    const task = this.transformations.find(t => t.key === this.selectedTransform);
                    if (!task) return '';
                    
                    const requiresDual = task.requires_dual_upload || false;
                    if (requiresDual && this.uploadedFiles.length < 2) {
                        return 'Upload 1 more file';
                    }
                    if (requiresDual && this.uploadedFiles.length > 2) {
                        return 'Only 2 files needed';
                    }
                    if (!requiresDual && this.uploadedFiles.length > 1) {
                        return 'Only 1 file needed';
                    }
                    
                    const allowedTypes = task.input_file_types || ['docx'];
                    const hasWrongType = this.uploadedFiles.some(f => !allowedTypes.includes(f.type));
                    if (hasWrongType) {
                        return `Need ${allowedTypes.map(t => t.toUpperCase()).join(' or ')} file`;
                    }
                    
                    return '';
                },
                
                get selectedTransformDesc() {
                    if (!this.selectedTransform) return '';
                    const t = this.transformations.find(x => x.key === this.selectedTransform);
                    return t ? t.description : '';
                },
                
                async addFile(event) {
                    const file = event.target.files[0];
                    if (!file) return;
                    
                    try {
                        const formData = new FormData();
                        formData.append('file', file);
                        
                        const response = await fetch('/api/upload', {
                            method: 'POST',
                            body: formData
                        });
                        
                        const data = await response.json();
                        if (data.success) {
                            this.uploadedFiles.push({
                                name: data.filename,
                                type: data.file_type,
                                path: data.file_path || '',
                                canvas_type: data.default_canvas_type,
                                column_headers: data.column_headers || []
                            });
                            
                            // Store column headers for Excel files
                            if (data.column_headers) {
                                this.excelColumnHeaders.push(data.column_headers);
                            }
                            
                            // Mark as uploaded for backward compatibility
                            this.docUploaded = true;
                            this.uploadedFileType = data.file_type;
                            this.defaultCanvasType = data.default_canvas_type;
                            
                            // Auto-handle dual Excel upload
                            if (this.uploadedFiles.length === 2 && 
                                this.uploadedFiles.every(f => f.type === 'xlsx' || f.type === 'xls')) {
                                await this.processDualExcel();
                            }
                            
                            // Update direction options if Align or Compare is selected
                            if (this.selectedTransform === 'align_excel' || this.selectedTransform === 'compare_excel') {
                                this.updateDynamicTaskOptions();
                            }
                            
                            event.target.value = ''; // Reset input to allow re-upload
                        }
                    } catch (error) {
                        console.error('Upload error:', error);
                        alert('Error uploading file');
                    }
                },
                
                removeFile(index) {
                    this.uploadedFiles.splice(index, 1);
                    this.excelColumnHeaders.splice(index, 1);
                    
                    if (this.uploadedFiles.length === 0) {
                        this.docUploaded = false;
                        this.selectedTransform = '';
                    }
                    
                    // Re-update dynamic options if align or compare is selected
                    if (this.selectedTransform === 'align_excel' || this.selectedTransform === 'compare_excel') {
                        this.updateDynamicTaskOptions();
                    }
                },
                
                // Labeled file upload methods
                async addLabeledFile(event, label) {
                    const file = event.target.files[0];
                    if (!file) return;
                    
                    try {
                        const formData = new FormData();
                        formData.append('file', file);
                        formData.append('label', label);
                        
                        const response = await fetch('/api/upload-labeled', {
                            method: 'POST',
                            body: formData
                        });
                        
                        const data = await response.json();
                        if (data.success) {
                            this.labeledFiles[label] = {
                                name: data.filename,
                                type: data.file_type,
                                label: data.label
                            };
                            
                            // Mark as uploaded
                            this.docUploaded = true;
                            
                            event.target.value = ''; // Reset input
                        } else {
                            alert('Error uploading file: ' + (data.error || 'Unknown error'));
                        }
                    } catch (error) {
                        console.error('Labeled upload error:', error);
                        alert('Error uploading file');
                    }
                },
                
                removeLabeledFile(label) {
                    delete this.labeledFiles[label];
                    
                    // If no labeled files remain, reset
                    if (Object.keys(this.labeledFiles).length === 0) {
                        this.docUploaded = false;
                    }
                },
                
                getFileIcon(fileType) {
                    const icons = {
                        'docx': '📄',
                        'xlsx': '📊',
                        'xls': '📊',
                        'txt': '📝',
                        'md': '📝',
                        'pdf': '📕'
                    };
                    return icons[fileType] || '📎';
                },
                
                get compatibleTransformations() {
                    if (this.uploadedFiles.length === 0) return [];
                    const fileTypesPresent = new Set(this.uploadedFiles.map(f => f.type));
                    const fileCount = this.uploadedFiles.length;
                    
                    return this.transformations.filter(t => {
                        const fileTypes = t.input_file_types || ['docx'];
                        const requiresDual = t.requires_dual_upload || false;
                        const allowsMultiple = t.allow_multiple_files || false;
                        
                        if (requiresDual) {
                            if (fileCount !== 2) return false;
                            return this.uploadedFiles.every(f => fileTypes.includes(f.type));
                        }
                        
                        if (allowsMultiple) {
                            return Array.from(fileTypesPresent).every(type => fileTypes.includes(type));
                        }
                        
                        return fileCount === 1 && fileTypes.includes(this.uploadedFiles[0].type);
                    });
                },
                
                async processDualExcel() {
                    // When two Excel files are uploaded, mark as ready for alignment
                    this.docUploaded = true;
                    this.uploadedFileType = 'xlsx';
                    this.defaultCanvasType = 'alignment_viewer';
                    
                    // Update options if align or compare is already selected
                    if (this.selectedTransform === 'align_excel' || this.selectedTransform === 'compare_excel') {
                        this.updateDynamicTaskOptions();
                    }
                },
                
                updateCanvasType() {
                    const selected = this.transformations.find(t => t.key === this.selectedTransform);
                    if (selected && selected.canvas_type) {
                        this.currentCanvasType = selected.canvas_type;
                    }
                    this.directionOptions = selected?.options || {};
                    
                    // Only reset options if changing to a different direction
                    // Don't reset when just updating dynamic options for same direction
                    if (!this.selectedTransform || this.lastSelectedTransform !== this.selectedTransform) {
                        this.selectedOptions = {};
                        
                        // Initialize with default option values
                        if (this.directionOptions) {
                            Object.keys(this.directionOptions).forEach(key => {
                                const option = this.directionOptions[key];
                                
                                // Set default based on option type
                                if (option.default !== undefined) {
                                    this.selectedOptions[key] = option.default;
                                } else {
                                    // Provide sensible defaults for each type if not specified
                                    switch(option.type) {
                                        case 'number':
                                            this.selectedOptions[key] = option.min || 0;
                                            break;
                                        case 'checkbox':
                                            this.selectedOptions[key] = false;
                                            break;
                                        case 'text':
                                            this.selectedOptions[key] = '';
                                            break;
                                        case 'textarea':
                                            this.selectedOptions[key] = '';
                                            break;
                                        default:
                                            // For select type, don't set a default (user must choose)
                                            this.selectedOptions[key] = '';
                                    }
                                }
                            });
                        }
                        
                        this.lastSelectedTransform = this.selectedTransform;
                    }
                    
                    // Update dynamic options for align_excel or compare_excel
                    if (this.selectedTransform === 'align_excel' || this.selectedTransform === 'compare_excel') {
                        this.updateDynamicTaskOptions();
                    }
                },
                
                updateDynamicTaskOptions() {
                    // For align_excel and compare_excel, dynamically populate column choices from uploaded files
                    if (this.selectedTransform !== 'align_excel' && this.selectedTransform !== 'compare_excel') return;
                    
                    const excelFiles = this.uploadedFiles.filter(f => f.type === 'xlsx' || f.type === 'xls');
                    
                    // Get base options from transformation config
                    const baseOptions = this.transformations.find(t => t.key === this.selectedTransform)?.options || {};
                    
                    // Keep the include_diff option from config and set default if not already set
                    if (baseOptions.include_diff) {
                        this.directionOptions.include_diff = baseOptions.include_diff;
                        if (!this.selectedOptions.include_diff && baseOptions.include_diff.default) {
                            this.selectedOptions.include_diff = baseOptions.include_diff.default;
                        }
                    }
                    
                    if (excelFiles.length >= 1 && excelFiles[0].column_headers && excelFiles[0].column_headers.length > 0) {
                        const headers1 = excelFiles[0].column_headers;
                        this.directionOptions.column1 = {
                            label: `Column from ${excelFiles[0].name}`,
                            description: 'Select which column to use for matching',
                            default: '0',
                            choices: headers1.map((header, idx) => ({
                                value: String(idx),
                                label: `${header}`
                            }))
                        };
                        // Set default if not already set
                        if (!this.selectedOptions.column1) {
                            this.selectedOptions.column1 = '0';
                        }
                    } else if (excelFiles.length >= 1) {
                        // Fallback if headers couldn't be read
                        this.directionOptions.column1 = {
                            label: 'Column from File 1',
                            description: 'Upload Excel file to see columns',
                            choices: []
                        };
                    }
                    
                    if (excelFiles.length >= 2 && excelFiles[1].column_headers && excelFiles[1].column_headers.length > 0) {
                        const headers2 = excelFiles[1].column_headers;
                        this.directionOptions.column2 = {
                            label: `Column from ${excelFiles[1].name}`,
                            description: 'Select which column to use for matching',
                            default: '0',
                            choices: headers2.map((header, idx) => ({
                                value: String(idx),
                                label: `${header}`
                            }))
                        };
                        // Set default if not already set
                        if (!this.selectedOptions.column2) {
                            this.selectedOptions.column2 = '0';
                        }
                    } else if (excelFiles.length >= 1) {
                        // Show message to upload second file
                        this.directionOptions.column2 = {
                            label: 'Column from File 2',
                            description: 'Upload a second Excel file to see columns',
                            choices: []
                        };
                    }
                },
                
                async rerunFromStep(stepIndex) {
                    if (!this.selectedTransform) return;
                    
                    // Get the edited content from the canvas
                    let editedContent = '';
                    if (this.stepOutputs[stepIndex]?.startsWith('AUDIO_FILE:')) {
                        editedContent = this.stepOutputs[stepIndex];
                    } else {
                        const editorDiv = document.getElementById('wysiwyg-editor');
                        if (editorDiv && this.turndownService) {
                            editedContent = this.turndownService.turndown(editorDiv.innerHTML);
                        } else {
                            editedContent = this.stepOutputs[stepIndex] || '';
                        }
                    }
                    
                    // Update current step output with edited content
                    this.stepOutputs[stepIndex] = editedContent;
                    
                    // Mark subsequent steps as pending and clear their outputs
                    for (let i = stepIndex + 1; i < this.steps.length; i++) {
                        this.steps[i].status = 'pending';
                        this.steps[i].statusText = '⏳';
                        this.stepOutputs[i] = '';
                    }
                    
                    this.processing = true;
                    this.currentStreamingStep = null;
                    this.userSelectedStep = false;
                    
                    // Call backend with rerun parameters
                    const optionsParam = encodeURIComponent(JSON.stringify(this.selectedOptions || {}));
                    const eventSource = new EventSource(
                        `/api/stream/${this.selectedTransform}?start_from_step=${stepIndex + 1}&edited_output=${encodeURIComponent(editedContent)}&options=${optionsParam}`
                    );
                    
                    this.setupEventSourceHandlers(eventSource);
                },
                
                areOptionsValid() {
                    const optionKeys = Object.keys(this.directionOptions || {});
                    if (!optionKeys.length) return true;
                    return optionKeys.every(key => {
                        const option = this.directionOptions[key];
                        const value = this.selectedOptions[key];
                        if (option?.required === false) return true;
                        return Boolean(value);
                    });
                },
                
                canRunTask() {
                    if (this.processing) return false;
                    if (!this.selectedTransform) return false;
                    if (!this.areOptionsValid()) return false;
                    
                    // Check direction requirements match uploaded files
                    const selected = this.transformations.find(t => t.key === this.selectedTransform);
                    if (!selected) return false;
                    
                    // For labeled file inputs, check those instead
                    if (this.currentTaskUsesLabeledFiles) {
                        return this.allLabeledFilesUploaded;
                    }
                    
                    // For traditional file uploads
                    if (this.uploadedFiles.length === 0) return false;
                    
                    const requiresDual = selected.requires_dual_upload || false;
                    const allowsMultiple = selected.allow_multiple_files || false;
                    
                    // Dual upload tasks need exactly 2 files
                    if (requiresDual && this.uploadedFiles.length !== 2) return false;
                    
                    // Regular tasks (not dual, not multiple) need exactly 1 file
                    if (!requiresDual && !allowsMultiple && this.uploadedFiles.length !== 1) return false;
                    
                    // Multiple file tasks need at least 1 file (already checked above)
                    // No additional constraint needed for allowsMultiple
                    
                    return true;
                },

                allowRerunFrom(idx) {
                    const step = this.steps[idx];
                    if (!step) return false;
                    if (idx < this.steps.length - 1) return true;
                    return step.step_type !== 'podcast_generator';
                },
                
                async runDraft() {
                    // Check if we have files uploaded (either traditional or labeled)
                    const hasTraditionalFiles = this.uploadedFiles.length > 0;
                    const hasLabeledFiles = Object.keys(this.labeledFiles).length > 0;
                    
                    if (!this.selectedTransform || (!hasTraditionalFiles && !hasLabeledFiles)) return;
                    
                    this.processing = true;
                    this.stepOutputs = [];
                    this.steps = [];
                    this.currentViewingStep = 0;
                    this.currentStreamingStep = null;
                    this.userSelectedStep = false;
                    
                    // Auto-collapse left panel when workflow starts to give Canvas more space
                    if (!this.leftPanelCollapsed) {
                        // Small delay so user sees the transition
                        setTimeout(() => {
                            this.leftPanelCollapsed = true;
                        }, 300);
                    }
                    
                    // Clear alignment editing state
                    this.alignmentData = null;
                    this.alignmentDataOriginal = null;
                    this.alignmentEditMode = false;
                    this.selectedOrphan1 = null;
                    this.selectedOrphan2 = null;
                    
                    // Clear chat state
                    this.chatMessages = [];
                    this.chatSessionId = null;
                    this.userQuestion = '';
                    this.isWaitingForChat = false;
                    
                    const optionsParam = encodeURIComponent(JSON.stringify(this.selectedOptions || {}));
                    const eventSource = new EventSource(`/api/stream/${this.selectedTransform}?options=${optionsParam}`);
                    
                    this.setupEventSourceHandlers(eventSource);
                },
                
                setupEventSourceHandlers(eventSource) {
                    eventSource.onmessage = (event) => {
                        const data = JSON.parse(event.data);
                        
                        if (data.type === 'step_status') {
                            if (!this.steps[data.step]) {
                                this.steps.push({ 
                                    name: data.name, 
                                    status: data.status, 
                                    statusText: this.getStatusText(data.status),
                                    step_type: data.step_type || 'llm_prompt'
                                });
                            } else {
                                this.steps[data.step].status = data.status;
                                this.steps[data.step].statusText = this.getStatusText(data.status);
                                if (data.step_type) {
                                    this.steps[data.step].step_type = data.step_type;
                                }
                            }
                        } 
                        else if (data.type === 'stream') {
                            this.currentStreamingStep = data.step;
                            
                            if (!this.userSelectedStep) {
                                this.currentViewingStep = data.step;
                            }
                            
                            this.stepOutputs[data.step] = data.text;
                        } 
                        else if (data.type === 'complete') {
                            this.processing = false;
                            eventSource.close();
                            
                            // Set currentViewingStep to the last step
                            if (!this.userSelectedStep) {
                                // Find the highest index in stepOutputs that has content
                                let maxIndex = -1;
                                for (let i = 0; i < this.stepOutputs.length; i++) {
                                    if (this.stepOutputs[i]) {
                                        maxIndex = i;
                                    }
                                }
                                if (maxIndex >= 0) {
                                    this.currentViewingStep = maxIndex;
                                }
                            }
                            
                            // Initialize chat session if canvas is chat_interface
                            if (this.currentCanvasType === 'chat_interface') {
                                this.$nextTick(() => {
                                    this.initializeChatSession();
                                });
                            }
                        } 
                        else if (data.type === 'error') {
                            console.error('ERROR:', data.message);
                            alert(data.message);
                            this.processing = false;
                            eventSource.close();
                        }
                    };
                    
                    eventSource.onerror = (error) => {
                        console.error('EventSource error:', error);
                        this.processing = false;
                        eventSource.close();
                    };
                },
                
                viewStep(index) {
                    if (this.stepOutputs[index] !== undefined) {
                        this.currentViewingStep = index;
                        this.userSelectedStep = true;
                        
                        // Clear alignment data when switching steps
                        this.alignmentData = null;
                        this.alignmentDataOriginal = null;
                        this.alignmentEditMode = false;
                        this.selectedOrphan1 = null;
                        this.selectedOrphan2 = null;
                    }
                },
                
                renderMarkdown(text) {
                    if (!text) return '<p class="text-gray-400 italic">No output yet...</p>';
                    
                    // Check if this is an audio file
                    if (text.startsWith('AUDIO_FILE:')) {
                        const filename = text.replace('AUDIO_FILE:', '').trim();
                        return this.renderAudioPlayer(filename);
                    }
                    
                    // Check if this is a redline diff
                    if (text.startsWith('REDLINE_DIFF:')) {
                        const jsonData = text.replace('REDLINE_DIFF:', '').trim();
                        return this.renderRedlineDiff(jsonData);
                    }
                    
                    try {
                        marked.setOptions({ breaks: true, gfm: true });
                        return marked.parse(text);
                    } catch (error) {
                        console.error('Markdown error:', error);
                        return `<pre>${text}</pre>`;
                    }
                },
                
                renderAudioPlayer(filename) {
                    return `
                        <div class="audio-player-container p-6 bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-200 rounded-lg">
                            <div class="mb-4 flex items-center gap-3">
                                <span class="text-3xl">🎙️</span>
                                <div>
                                    <h3 class="text-lg font-bold text-gray-900">Podcast Generated!</h3>
                                    <p class="text-sm text-gray-600">Click play to listen to your audio podcast</p>
                                </div>
                            </div>
                            <audio controls class="w-full mb-3" style="border-radius: 8px;">
                                <source src="/api/audio/${filename}" type="audio/mpeg">
                                Your browser does not support the audio element.
                            </audio>
                            <div class="text-xs text-gray-500">
                                <p>📁 File: ${filename}</p>
                                <p class="mt-1">💡 Tip: Right-click the audio player and select "Download" to save the podcast</p>
                            </div>
                        </div>
                    `;
                },
                
                renderRedlineDiff(jsonData) {
                    try {
                        const result = JSON.parse(jsonData);
                        
                        const removedCount = result.removed_words || 0;
                        const addedCount = result.added_words || 0;
                        const unchangedCount = result.unchanged_words || 0;
                        const changePercentage = result.change_percentage || 0;
                        const doc1Label = result.doc1_label || 'Document 1';
                        const doc2Label = result.doc2_label || 'Document 2';
                        
                        // Generate unique ID for this diff instance
                        const diffId = 'diff_' + Math.random().toString(36).substr(2, 9);
                        
                        // Process diff HTML to use new class names
                        let processedDiff = result.diff_html;
                        processedDiff = processedDiff.replace(/class="diff-removed"/g, 'class="diff-deleted"');
                        processedDiff = processedDiff.replace(/class="diff-added"/g, 'class="diff-inserted"');
                        
                        return `
                            <div class="mb-6" x-data="{ showMarkup_${diffId}: true }">
                                <!-- Document Container -->
                                <div class="diff-document-container">
                                    <!-- Header -->
                                    <div class="diff-document-header">
                                        <div class="diff-document-title">📝 Document Comparison</div>
                                        <div class="diff-document-subtitle">
                                            Comparing: <strong>${doc1Label}</strong> → <strong>${doc2Label}</strong>
                                        </div>
                                    </div>
                                    
                                    <!-- Stats Bar -->
                                    <div class="diff-stats-bar">
                                        <div class="diff-stat-item">
                                            <span>Deletions:</span>
                                            <span class="diff-stat-badge deletions">${removedCount}</span>
                                        </div>
                                        <div class="diff-stat-item">
                                            <span>Insertions:</span>
                                            <span class="diff-stat-badge insertions">${addedCount}</span>
                                        </div>
                                        <div class="diff-stat-item">
                                            <span>Total Changed:</span>
                                            <span class="diff-stat-badge changes">${changePercentage.toFixed(1)}%</span>
                                        </div>
                                    </div>
                                    
                                    <!-- View Toggle -->
                                    <div class="diff-view-toggle">
                                        <button 
                                            class="diff-toggle-button"
                                            :class="{ 'active': showMarkup_${diffId} }"
                                            @click="showMarkup_${diffId} = true">
                                            All Markup
                                        </button>
                                        <button 
                                            class="diff-toggle-button"
                                            :class="{ 'active': !showMarkup_${diffId} }"
                                            @click="showMarkup_${diffId} = false">
                                            Final View
                                        </button>
                                    </div>
                                    
                                    <!-- Document Body with Markup -->
                                    <div class="diff-document-body" x-show="showMarkup_${diffId}">
                                        ${processedDiff}
                                    </div>
                                    
                                    <!-- Document Body without Markup (Final) -->
                                    <div class="diff-document-body" x-show="!showMarkup_${diffId}" style="display: none;">
                                        ${this.stripDiffMarkup(processedDiff)}
                                    </div>
                                    
                                    <!-- Legend -->
                                    <div class="diff-legend" x-show="showMarkup_${diffId}">
                                        <div class="diff-legend-item">
                                            <span class="diff-legend-sample deleted">Deleted text</span>
                                            <span>— Text removed from original</span>
                                        </div>
                                        <div class="diff-legend-item">
                                            <span class="diff-legend-sample inserted">Inserted text</span>
                                            <span>— Text added in revision</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        `;
                    } catch (error) {
                        console.error('Error rendering redline diff:', error);
                        return `<div class="text-red-600">Error rendering diff: ${error.message}</div>`;
                    }
                },
                
                stripDiffMarkup(html) {
                    // Remove deleted text and markup, keep only inserted/unchanged text
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    
                    // Remove all deleted elements
                    doc.querySelectorAll('.diff-deleted').forEach(el => el.remove());
                    
                    // Clean up inserted elements (keep text, remove styling)
                    doc.querySelectorAll('.diff-inserted').forEach(el => {
                        const text = document.createTextNode(el.textContent);
                        el.replaceWith(text);
                    });
                    
                    return doc.body.innerHTML;
                },
                
                renderAlignmentViewer(text) {
                    if (!text) return '<p class="text-gray-400 italic">No alignment results yet...</p>';
                    
                    // Check if this is Excel alignment result data
                    if (text.startsWith('ALIGNMENT_RESULT:')) {
                        const jsonData = text.replace('ALIGNMENT_RESULT:', '').trim();
                        try {
                            const result = JSON.parse(jsonData);
                            
                            // Store alignment data for editing
                            // Always update alignmentData to capture changes from subsequent steps (e.g., AI analysis)
                            this.alignmentData = JSON.parse(JSON.stringify(result)); // Deep copy
                            if (!this.alignmentDataOriginal) {
                                this.alignmentDataOriginal = JSON.parse(JSON.stringify(result)); // Store original only once
                            }
                            
                            const hasDiff = result.include_diff;
                            const hasAnalysis = result.has_analysis;
                            
                            let html = `
                                <div class="alignment-viewer-container p-6 bg-gradient-to-br from-emerald-50 to-blue-50 border-2 border-emerald-200 rounded-lg">
                                    <div class="mb-6">
                                        <div class="flex items-center gap-3 mb-2">
                                            <span class="text-3xl">${hasAnalysis ? '🔍' : '🔗'}</span>
                                            <h3 class="text-2xl font-bold text-gray-900">${hasAnalysis ? 'Excel Comparison Results' : 'Excel Alignment Results'}</h3>
                                        </div>
                                        <div class="grid grid-cols-3 gap-4 mt-4">
                                            <div class="bg-white rounded-lg p-4 border border-emerald-200">
                                                <p class="text-sm text-gray-600">Total Matches</p>
                                                <p class="text-3xl font-bold text-emerald-600">${result.total_matches}</p>
                                            </div>
                                            <div class="bg-white rounded-lg p-4 border border-amber-200">
                                                <p class="text-sm text-gray-600">Orphans</p>
                                                <p class="text-3xl font-bold text-amber-600">${result.total_orphans}</p>
                                            </div>
                                            <div class="bg-white rounded-lg p-4 border border-blue-200">
                                                <p class="text-sm text-gray-600">Avg Similarity</p>
                                                <p class="text-3xl font-bold text-blue-600">${(result.avg_similarity * 100).toFixed(1)}%</p>
                                            </div>
                                        </div>
                                        ${hasDiff ? '<p class="text-xs text-gray-500 mt-3">✨ Diff highlighting enabled</p>' : ''}
                                        ${hasAnalysis ? '<p class="text-xs text-gray-500 mt-3">🤖 AI-generated comparison analysis added</p>' : ''}
                                    </div>
                                    
                                    <div class="space-y-6">
                                        <div>
                                            <h4 class="text-lg font-semibold text-gray-900 mb-3">🎯 Matched Pairs</h4>
                                            <div class="bg-white rounded-lg border border-gray-200 overflow-hidden">
                                                <table class="w-full text-sm">
                                                    <thead class="bg-gray-50 border-b border-gray-200">
                                                        <tr>
                                                            <th class="px-4 py-3 text-left font-semibold text-gray-700 w-1/4">${result.file1_column}</th>
                                                            <th class="px-4 py-3 text-left font-semibold text-gray-700 w-1/4">${result.file2_column}</th>
                                                            ${hasDiff ? '<th class="px-4 py-3 text-left font-semibold text-purple-700 w-1/4">Diff</th>' : ''}
                                                            ${hasAnalysis ? '<th class="px-4 py-3 text-left font-semibold text-blue-700">AI Analysis</th>' : ''}
                                                            <th class="px-4 py-3 text-left font-semibold text-gray-700 w-24">Similarity</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>`;
                            
                            result.matched_pairs.forEach((pair, idx) => {
                                const similarityColor = pair.similarity > 0.8 ? 'text-emerald-600' : 
                                                       pair.similarity > 0.6 ? 'text-blue-600' : 'text-amber-600';
                                html += `
                                    <tr class="${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'} hover:bg-blue-50 transition">
                                        <td class="px-4 py-3 border-b border-gray-100">${pair.file1_value}</td>
                                        <td class="px-4 py-3 border-b border-gray-100">${pair.file2_value}</td>`;
                                
                                if (hasDiff && pair.diff) {
                                    html += `<td class="px-4 py-3 border-b border-gray-100 diff-content">${pair.diff}</td>`;
                                }
                                
                                                if (hasAnalysis && pair.analysis) {
                                                    html += `<td class="px-4 py-3 border-b border-gray-100 text-gray-700 italic text-xs leading-relaxed">${pair.analysis}</td>`;
                                                }
                                
                                html += `
                                        <td class="px-4 py-3 border-b border-gray-100">
                                            <span class="font-semibold ${similarityColor}">${(pair.similarity * 100).toFixed(1)}%</span>
                                        </td>
                                    </tr>`;
                            });
                            
                            html += `
                                                    </tbody>
                                                </table>
                                            </div>
                                        </div>`;
                            
                            if (result.orphans_file1.length > 0 || result.orphans_file2.length > 0) {
                                html += `
                                    <div>
                                        <h4 class="text-lg font-semibold text-gray-900 mb-3">⚠️ Unmatched Items (Orphans)</h4>
                                        <div class="grid grid-cols-2 gap-4">`;
                                
                                if (result.orphans_file1.length > 0) {
                                    html += `
                                        <div class="bg-white rounded-lg border border-amber-200 p-4">
                                            <p class="font-semibold text-amber-700 mb-2">File 1 Orphans (${result.orphans_file1.length})</p>
                                            <ul class="space-y-1 text-sm text-gray-700">`;
                                    result.orphans_file1.forEach(orphan => {
                                        html += `<li class="px-3 py-2 bg-amber-50 rounded">• ${orphan.value}</li>`;
                                    });
                                    html += `</ul></div>`;
                                }
                                
                                if (result.orphans_file2.length > 0) {
                                    html += `
                                        <div class="bg-white rounded-lg border border-amber-200 p-4">
                                            <p class="font-semibold text-amber-700 mb-2">File 2 Orphans (${result.orphans_file2.length})</p>
                                            <ul class="space-y-1 text-sm text-gray-700">`;
                                    result.orphans_file2.forEach(orphan => {
                                        html += `<li class="px-3 py-2 bg-amber-50 rounded">• ${orphan.value}</li>`;
                                    });
                                    html += `</ul></div>`;
                                }
                                
                                html += `</div></div>`;
                            }
                            
                            html += `</div></div>`;
                            return html;
                            
                        } catch (error) {
                            console.error('Error parsing alignment result:', error);
                            return `<pre class="p-4 bg-gray-100 rounded">${text}</pre>`;
                        }
                    }
                    
                    // Fallback to regular markdown
                    try {
                        marked.setOptions({ breaks: true, gfm: true });
                        return marked.parse(text);
                    } catch (error) {
                        return `<pre>${text}</pre>`;
                    }
                },
                
                // Diff Viewer Functions
                initializeDiffViewer() {
                    if (!this.stepOutputs || this.stepOutputs.length === 0) return;
                    
                    // Parse different step outputs
                    this.stepOutputs.forEach((output, idx) => {
                        if (output.startsWith('ENHANCED_DIFF:')) {
                            const jsonData = output.replace('ENHANCED_DIFF:', '').trim();
                            try {
                                this.diffData = JSON.parse(jsonData);
                            } catch (error) {
                                console.error('Error parsing enhanced diff:', error);
                            }
                        } else if (output.startsWith('STRUCTURAL_ANALYSIS:')) {
                            const jsonData = output.replace('STRUCTURAL_ANALYSIS:', '').trim();
                            try {
                                this.structuralData = JSON.parse(jsonData);
                            } catch (error) {
                                console.error('Error parsing structural analysis:', error);
                            }
                        } else if (output.startsWith('SEMANTIC_DIFF:')) {
                            const jsonData = output.replace('SEMANTIC_DIFF:', '').trim();
                            try {
                                this.semanticData = JSON.parse(jsonData);
                            } catch (error) {
                                console.error('Error parsing semantic diff:', error);
                            }
                        }
                    });
                },
                
                renderSplitDoc1() {
                    if (!this.diffData || !this.diffData.changes_by_type) return '';
                    
                    // Get original document content (words without added ones)
                    const changes = this.diffData.changes_by_type;
                    let html = '<div class="space-y-1">';
                    
                    // Simplified rendering for split view
                    // Show deletions highlighted in red
                    const deletions = changes.deletions || [];
                    if (deletions.length > 0) {
                        deletions.forEach(del => {
                            html += `<div class="text-xs p-1 bg-red-50 border-l-2 border-red-500">
                                <span class="text-red-700 line-through">${del.word}</span>
                            </div>`;
                        });
                    }
                    
                    html += '</div>';
                    return html;
                },
                
                renderSplitDoc2() {
                    if (!this.diffData || !this.diffData.changes_by_type) return '';
                    
                    // Get new document content (words without removed ones)
                    const changes = this.diffData.changes_by_type;
                    let html = '<div class="space-y-1">';
                    
                    // Show additions highlighted in green
                    const additions = changes.additions || [];
                    if (additions.length > 0) {
                        additions.forEach(add => {
                            html += `<div class="text-xs p-1 bg-emerald-50 border-l-2 border-emerald-500">
                                <span class="text-emerald-700 font-medium">${add.word}</span>
                            </div>`;
                        });
                    }
                    
                    html += '</div>';
                    return html;
                },
                
                formatText(command) {
                    // Apply formatting to selected text
                    const editor = document.getElementById('wysiwyg-editor');
                    if (!editor) return;
                    
                    editor.focus();
                    
                    if (command === 'h1') {
                        document.execCommand('formatBlock', false, 'h1');
                    } else if (command === 'h2') {
                        document.execCommand('formatBlock', false, 'h2');
                    } else if (command === 'h3') {
                        document.execCommand('formatBlock', false, 'h3');
                    } else if (command === 'paragraph') {
                        document.execCommand('formatBlock', false, 'p');
                    } else {
                        document.execCommand(command, false, null);
                    }
                    
                    // Update markdown after formatting
                    this.updateMarkdownFromHTML(editor);
                },
                
                updateMarkdownFromHTML(element) {
                    // Convert edited HTML back to Markdown
                    if (!this.processing && this.turndownService && element) {
                        try {
                            const html = element.innerHTML;
                            const markdown = this.turndownService.turndown(html);
                            this.stepOutputs[this.currentViewingStep] = markdown;
                        } catch (error) {
                            console.error('HTML to Markdown conversion error:', error);
                        }
                    }
                },
                
                async exportToWord() {
                    try {
                        const text = this.stepOutputs[this.currentViewingStep] || '';
                        
                        const response = await fetch('/api/export', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ text })
                        });
                        
                        const blob = await response.blob();
                        this.downloadUrl = URL.createObjectURL(blob);
                        
                        const a = document.createElement('a');
                        a.href = this.downloadUrl;
                        a.download = 'transformed_document.docx';
                        a.click();
                    } catch (error) {
                        console.error('Export error:', error);
                        alert('Export failed');
                    }
                },
                
                getStatusText(status) {
                    const map = { pending: '⏳', processing: '⚡', completed: '✅', error: '❌' };
                    return map[status] || '';
                },
                
                startAddTransformation() {
                    this.addingTransform = true;
                    this.editData = { name: '', key: '', description: '', steps: [], options: {} };
                },
                
                async editTransformation(key) {
                    try {
                        const response = await fetch(`/api/transformation/${key}`);
                        const data = await response.json();
                        data.options = data.options || {};
                        data.steps = data.steps || [];
                        this.editData = data;
                        this.editingTransform = true;
                    } catch (error) {
                        console.error('Error loading transformation:', error);
                    }
                },
                
                async duplicateTransformation(key) {
                    try {
                        const response = await fetch(`/api/transformation/${key}/duplicate`, {
                            method: 'POST'
                        });
                        
                        const result = await response.json();
                        
                        if (result.success) {
                            // Reload transformations list
                            await this.loadTransformations();
                            
                            // Show success message and offer to edit
                            if (confirm(`✅ Workflow duplicated as "${result.new_name}". Do you want to edit it now?`)) {
                                window.location.href = `/workflow-builder?edit=${result.new_key}`;
                            }
                        } else {
                            alert(`Error: ${result.error}`);
                        }
                    } catch (error) {
                        console.error('Duplicate error:', error);
                        alert('Error duplicating workflow');
                    }
                },
                
                async deleteTransformation(key) {
                    if (!confirm('Delete this workflow?')) return;
                    
                    try {
                        await fetch(`/api/transformation/${key}`, { method: 'DELETE' });
                        await this.loadTransformations();
                    } catch (error) {
                        console.error('Delete error:', error);
                    }
                },
                
                async saveTransformation() {
                    try {
                        const method = this.addingTransform ? 'POST' : 'PUT';
                        const url = this.addingTransform ? '/api/transformation' : `/api/transformation/${this.editData.key}`;
                        
                        await fetch(url, {
                            method,
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(this.editData)
                        });
                        
                        this.cancelEdit();
                        await this.loadTransformations();
                    } catch (error) {
                        console.error('Save error:', error);
                        alert('Save failed');
                    }
                },
                
                cancelEdit() {
                    this.editingTransform = false;
                    this.addingTransform = false;
                    this.editData = { steps: [], options: {} };
                },
                
                addStep() {
                    this.editData.steps.push({ 
                        step_name: '', 
                        prompt: '', 
                        step_type: 'llm_prompt',
                        parameters: {}
                    });
                },
                
                removeStep(idx) {
                    this.editData.steps.splice(idx, 1);
                },
                
                getToolDescription(toolType) {
                    const descriptions = {
                        'llm_prompt': 'Uses GPT to generate, transform, or analyze text based on your prompt.',
                        'alignment': 'Matches items from two Excel files using OpenAI embeddings and Hungarian algorithm.',
                        'compare_analysis': 'Loops through aligned pairs and generates natural language descriptions of differences.',
                        'podcast_generator': 'Converts text to speech using OpenAI TTS with selectable voice.',
                        'fact_check': 'Extracts claims and verifies them using web search.',
                        'web_search': 'Searches the web for information using DuckDuckGo.',
                        'content_enrichment': 'Adds context and details from web research.',
                        'data_validation': 'Validates data formats, checks for errors.',
                        'document_analysis': 'Extracts numbers, dates, emails, headings, or word counts.'
                    };
                    return descriptions[toolType] || 'Select a tool type to see description.';
                },
                
                getToolName(toolType) {
                    const names = {
                        'llm_prompt': '💬 LLM Prompt',
                        'alignment': '🔗 Alignment',
                        'compare_analysis': '🔍 Compare Analysis',
                        'podcast_generator': '🎙️ Podcast Generator',
                        'fact_check': '✓ Fact Check',
                        'web_search': '🌐 Web Search',
                        'content_enrichment': '➕ Content Enrichment',
                        'data_validation': '📋 Data Validation',
                        'document_analysis': '📊 Document Analysis'
                    };
                    return names[toolType] || toolType;
                },

                addOption() {
                    const key = prompt('Option key (lowercase, no spaces):');
                    if (!key) return;
                    if (!this.editData.options) this.editData.options = {};
                    if (this.editData.options[key]) {
                        alert('Option with this key already exists.');
                        return;
                    }
                    this.editData.options[key] = {
                        label: '',
                        description: '',
                        required: true,
                        choices: []
                    };
                },

                removeOption(key) {
                    if (!confirm('Remove this option?')) return;
                    if (this.editData.options) {
                        delete this.editData.options[key];
                    }
                },

                addOptionChoice(key) {
                    const option = this.editData.options?.[key];
                    if (!option) return;
                    option.choices.push({ value: '', label: '' });
                },

                removeOptionChoice(key, index) {
                    const option = this.editData.options?.[key];
                    if (!option) return;
                    option.choices.splice(index, 1);
                }
            }
        }
