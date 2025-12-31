/**
 * Certificate Canvas Renderer
 * Renders certificates in the browser using HTML5 Canvas.
 * Eliminates server-side font dependencies.
 */

class CertificateRenderer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.templateImage = null;
        this.certificateData = null;
    }

    /**
     * Load certificate data from API and render
     */
    async load(participantId) {
        try {
            const response = await fetch(`/api/certificate-data/${participantId}`);
            if (!response.ok) {
                throw new Error('Failed to load certificate data');
            }

            this.certificateData = await response.json();

            if (this.certificateData.error) {
                throw new Error(this.certificateData.error);
            }

            if (this.certificateData.type === 'custom') {
                // Custom certificate - just load and display the image
                await this.loadAndRenderCustom(this.certificateData.certificate_url);
            } else {
                // Template-based - load template and overlay name
                await this.loadAndRenderTemplate();
            }

            return true;
        } catch (error) {
            console.error('Certificate render error:', error);
            return false;
        }
    }

    /**
     * Load custom certificate image
     */
    async loadAndRenderCustom(imageUrl) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.crossOrigin = 'anonymous';
            img.onload = () => {
                this.canvas.width = img.width;
                this.canvas.height = img.height;
                this.ctx.drawImage(img, 0, 0);
                this.templateImage = img;
                resolve();
            };
            img.onerror = () => reject(new Error('Failed to load certificate image'));
            img.src = imageUrl;
        });
    }

    /**
     * Load template and render with name overlay
     */
    async loadAndRenderTemplate() {
        const data = this.certificateData;

        return new Promise((resolve, reject) => {
            const img = new Image();
            img.crossOrigin = 'anonymous';
            img.onload = () => {
                // Set canvas size to match template
                this.canvas.width = img.width;
                this.canvas.height = img.height;

                // Draw template
                this.ctx.drawImage(img, 0, 0);
                this.templateImage = img;

                // Calculate position
                const x = (data.x_percent / 100) * img.width;
                const y = (data.y_percent / 100) * img.height;

                // Scale font size based on image size
                // Assuming preview is around 800px, scale proportionally
                const scaleFactor = img.width / 800;
                const fontSize = Math.round(data.font_size * scaleFactor);

                // Set font
                this.ctx.font = `${data.font_weight} ${fontSize}px ${data.font_family}`;
                this.ctx.fillStyle = data.font_color;
                this.ctx.textAlign = 'center';
                this.ctx.textBaseline = 'middle';

                // Draw name
                this.ctx.fillText(data.name, x, y);

                resolve();
            };
            img.onerror = () => reject(new Error('Failed to load template'));
            img.src = data.template_url;
        });
    }

    /**
     * Download the rendered certificate as PNG
     */
    download(filename) {
        const link = document.createElement('a');
        link.download = filename || 'certificate.png';
        link.href = this.canvas.toDataURL('image/png');
        link.click();
    }

    /**
     * Get the certificate as a data URL
     */
    getDataURL() {
        return this.canvas.toDataURL('image/png');
    }

    /**
     * Get the certificate as a Blob
     */
    getBlob() {
        return new Promise((resolve) => {
            this.canvas.toBlob((blob) => {
                resolve(blob);
            }, 'image/png');
        });
    }
}

// Export for use
window.CertificateRenderer = CertificateRenderer;
