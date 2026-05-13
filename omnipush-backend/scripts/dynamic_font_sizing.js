/**
 * Dynamic Font Sizing Utility
 * Automatically adjusts font size to fit text within given container dimensions
 */

class DynamicFontSizer {
  constructor(options = {}) {
    this.options = {
      minFontSize: 24,
      maxFontSize: 120,
      precision: 0.5,
      lineHeightRatio: 1.1,
      paddingBuffer: 2,
      maxIterations: 50,
      debounceDelay: 100,
      preferLargerSizes: true,
      targetFillRatio: 0.85, // Aim to fill 85% of available space
      ...options
    };

    this.resizeTimeout = null;
    this.resizeObserver = null;
  }

  /**
   * Calculate the optimal font size for text to fit within container
   * @param {HTMLElement} textElement - The element containing the text
   * @param {HTMLElement} container - The container element (optional, defaults to parent)
   * @param {Object} constraints - Additional constraints
   * @returns {number} - The optimal font size in pixels
   */
  fitText(textElement, container = null, constraints = {}) {
    if (!textElement) return this.options.minFontSize;

    container = container || textElement.parentElement;
    if (!container) return this.options.minFontSize;

    // Merge constraints with default options
    const options = { ...this.options, ...constraints };

    // Get container dimensions - use more precise measurement
    let containerRect, availableWidth, availableHeight;

    if (container.getBoundingClientRect) {
      containerRect = container.getBoundingClientRect();
      const containerStyle = window.getComputedStyle(container);

      // Calculate available space accounting for padding and borders
      availableWidth = containerRect.width -
        parseFloat(containerStyle.paddingLeft || 0) -
        parseFloat(containerStyle.paddingRight || 0) -
        parseFloat(containerStyle.borderLeftWidth || 0) -
        parseFloat(containerStyle.borderRightWidth || 0) -
        options.paddingBuffer;

      availableHeight = containerRect.height -
        parseFloat(containerStyle.paddingTop || 0) -
        parseFloat(containerStyle.paddingBottom || 0) -
        parseFloat(containerStyle.borderTopWidth || 0) -
        parseFloat(containerStyle.borderBottomWidth || 0) -
        options.paddingBuffer;
    } else {
      // Fallback for virtual containers
      availableWidth = parseFloat(container.style.width) - options.paddingBuffer;
      availableHeight = parseFloat(container.style.height) - options.paddingBuffer;
    }

    if (availableWidth <= 0 || availableHeight <= 0) {
      return options.minFontSize;
    }

    // Store original styles
    const originalStyle = {
      fontSize: textElement.style.fontSize,
      lineHeight: textElement.style.lineHeight,
      whiteSpace: textElement.style.whiteSpace,
      overflow: textElement.style.overflow,
      visibility: textElement.style.visibility,
      position: textElement.style.position,
      width: textElement.style.width,
      height: textElement.style.height
    };

    // Set up for measurement - ensure proper text wrapping
    textElement.style.whiteSpace = 'normal';
    textElement.style.overflow = 'visible';
    textElement.style.visibility = 'visible';
    textElement.style.position = 'relative';
    textElement.style.width = `${availableWidth}px`;
    textElement.style.height = 'auto';

    let optimalSize = this.improvedBinarySearch(
      textElement,
      availableWidth,
      availableHeight,
      options
    );

    // Restore original styles
    Object.assign(textElement.style, originalStyle);

    // Apply the optimal font size
    textElement.style.fontSize = `${optimalSize}px`;
    textElement.style.lineHeight = options.lineHeightRatio;
    textElement.style.visibility = 'visible';

    return optimalSize;
  }

  /**
   * Reliable step-down algorithm for optimal font size
   */
  improvedBinarySearch(element, maxWidth, maxHeight, options) {
    const textLength = element.textContent.length;

    // Set reasonable minimum sizes based on content length
    let minSize = options.minFontSize;
    if (textLength <= 20) {
      minSize = Math.max(minSize, 50);
    } else if (textLength <= 50) {
      minSize = Math.max(minSize, 40);
    } else if (textLength <= 100) {
      minSize = Math.max(minSize, 32);
    } else {
      minSize = Math.max(minSize, 24);
    }

    // Start from a reasonable maximum and work down
    let currentSize = Math.min(options.maxFontSize, Math.floor(maxHeight * 0.7));

    // Ensure we don't start below minimum
    currentSize = Math.max(currentSize, minSize);

    function testFit(fontSize) {
      element.style.fontSize = `${fontSize}px`;
      element.style.lineHeight = options.lineHeightRatio;

      // Force layout recalculation
      element.offsetHeight;
      element.scrollHeight;

      const rect = element.getBoundingClientRect();

      // Check both width and height with small tolerance
      const widthFits = rect.width <= maxWidth + 1;
      const heightFits = rect.height <= maxHeight + 1;

      return widthFits && heightFits;
    }

    // First, try the starting size
    if (testFit(currentSize)) {
      return currentSize;
    }

    // Step down by 2px until it fits
    while (currentSize >= minSize) {
      if (testFit(currentSize)) {
        return currentSize;
      }
      currentSize -= 2;
    }

    // If nothing worked, try stepping down by 1px from minimum + 10
    currentSize = minSize + 10;
    while (currentSize >= minSize) {
      if (testFit(currentSize)) {
        return currentSize;
      }
      currentSize -= 1;
    }

    // Last resort: return minimum size
    element.style.fontSize = `${minSize}px`;
    return minSize;
  }

  /**
   * Legacy binary search algorithm (kept for compatibility)
   */
  binarySearchFontSize(element, maxWidth, maxHeight, options) {
    return this.improvedBinarySearch(element, maxWidth, maxHeight, options);
  }

  /**
   * Fit text using a more precise step-down approach
   */
  stepDownFontSize(element, maxWidth, maxHeight, options) {
    let currentSize = options.maxFontSize;

    while (currentSize >= options.minFontSize) {
      element.style.fontSize = `${currentSize}px`;
      element.style.lineHeight = options.lineHeightRatio;

      // Force reflow
      element.offsetHeight;

      const rect = element.getBoundingClientRect();

      if (rect.width <= maxWidth && rect.height <= maxHeight) {
        return currentSize;
      }

      currentSize -= options.precision;
    }

    return options.minFontSize;
  }

  /**
   * Set up automatic resizing with debouncing
   */
  autoResize(textElement, container = null, constraints = {}) {
    const resizeHandler = () => {
      clearTimeout(this.resizeTimeout);
      this.resizeTimeout = setTimeout(() => {
        this.fitText(textElement, container, constraints);
      }, this.options.debounceDelay);
    };

    // Window resize handler
    window.addEventListener('resize', resizeHandler);

    // Container resize observer
    if ('ResizeObserver' in window) {
      this.resizeObserver = new ResizeObserver(resizeHandler);
      this.resizeObserver.observe(container || textElement.parentElement);
    }

    // Image load handler (if text depends on images)
    const images = document.querySelectorAll('img');
    images.forEach(img => {
      if (!img.complete) {
        img.addEventListener('load', resizeHandler);
      }
    });

    // Initial sizing
    this.fitText(textElement, container, constraints);

    // Return cleanup function
    return () => {
      clearTimeout(this.resizeTimeout);
      window.removeEventListener('resize', resizeHandler);
      if (this.resizeObserver) {
        this.resizeObserver.disconnect();
      }
    };
  }

  /**
   * Fit multiple text elements simultaneously
   */
  fitMultipleTexts(elements, constraints = {}) {
    const results = [];

    elements.forEach(({ textElement, container, options: elementOptions }) => {
      const mergedOptions = { ...constraints, ...elementOptions };
      const fontSize = this.fitText(textElement, container, mergedOptions);
      results.push({ element: textElement, fontSize });
    });

    return results;
  }
}

// Simplified function for quick use
function fitTextToContainer(textElement, container = null, options = {}) {
  const sizer = new DynamicFontSizer(options);
  return sizer.fitText(textElement, container);
}

// Auto-resize function for easy setup
function setupAutoResize(textElement, container = null, options = {}) {
  const sizer = new DynamicFontSizer(options);
  return sizer.autoResize(textElement, container, options);
}

// Legacy function name for compatibility
function adjustFontSize(textElement, container = null, options = {}) {
  return fitTextToContainer(textElement, container, options);
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    DynamicFontSizer,
    fitTextToContainer,
    setupAutoResize,
    adjustFontSize
  };
}