import { useEffect, useRef, useState } from "react";
import { ChevronDown, Check } from "lucide-react";

function MultiSelect({
  label,
  options,
  selected,
  onChange,
  placeholder = "Select...",
}) {
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target)
      ) {
        setOpen(false);
      }
    }

    document.addEventListener(
      "mousedown",
      handleClickOutside
    );

    return () => {
      document.removeEventListener(
        "mousedown",
        handleClickOutside
      );
    };
  }, []);

  function toggleOption(option) {
    if (selected.includes(option)) {
      onChange(
        selected.filter(
          (item) => item !== option
        )
      );
    } else {
      onChange([...selected, option]);
    }
  }

  return (
    <div
      className="filter-field multi-select-field"
      ref={dropdownRef}
    >
      <span>{label}</span>

      <button
        type="button"
        className={`multi-select-trigger ${
          open ? "open" : ""
        }`}
        onClick={() => setOpen(!open)}
      >
        <span
          className={
            selected.length === 0
              ? "multi-select-placeholder"
              : ""
          }
        >
          {selected.length === 0
            ? placeholder
            : `${selected.length} selected`}
        </span>

        <ChevronDown
          size={16}
          className={open ? "rotate" : ""}
        />
      </button>

      {open && (
        <div className="multi-select-menu">

          {options.length === 0 ? (
            <div className="multi-select-empty">
              No options available
            </div>
          ) : (
            options.map((option) => {
              const isSelected =
                selected.includes(option);

              return (
                <button
                  type="button"
                  key={option}
                  className={`multi-select-option ${
                    isSelected ? "selected" : ""
                  }`}
                  onClick={() =>
                    toggleOption(option)
                  }
                >
                  <span className="checkbox">
                    {isSelected && (
                      <Check size={13} />
                    )}
                  </span>

                  <span>
                    {option}
                  </span>
                </button>
              );
            })
          )}

        </div>
      )}
    </div>
  );
}

export default MultiSelect;