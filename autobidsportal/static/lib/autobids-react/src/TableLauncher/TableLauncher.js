import React, { useState } from "react";
import PropTypes from "prop-types";

import TableLauncherRow from "./TableLauncherRow";

function TableLauncher(props) {
  const { rowInfo, cfmm2tarUrl, mutable } = props;
  const [activeIds, setActiveIds] = useState([]);

  function changeActiveId(id, isActive) {
    setActiveIds((state, props) => {
      const newState = [...state];
      if (state.includes(id) && !isActive) {
        newState.splice(state.indexOf(id), 1);
      } else if (!state.includes(id) && isActive) {
        newState.push(id);
      }
      return newState;
    });
  }

  function selectAll() {
    setActiveIds(props.rowInfo.map((row) => row.id));
  }

  function deselectAll() {
    setActiveIds([]);
  }

  return (
    <form method="POST" action={cfmm2tarUrl}>
      <div className="table-responsive" style={{ maxHeight: "400px" }}>
        <table className="table table-light overflow-auto">
          <thead>
            <tr>
              <th scope="col">Include in tar2bids</th>
              <th scope="col">Tar File</th>
              <th scope="col">Date</th>
              <th scope="col">Delete</th>
            </tr>
          </thead>
          <tbody>
            {rowInfo.map((child) => (
              <TableLauncherRow
                id={child.id}
                key={child.id}
                fileName={child.fileName}
                date={child.date}
                isActive={activeIds.includes(child.id)}
                deleteUrl={child.deleteUrl}
                renameUrl={child.renameUrl}
                updateActive={changeActiveId}
                mutable={mutable}
              />
            ))}
          </tbody>
        </table>
      </div>
      <button
        type="button"
        className="btn btn-secondary btn-sm me-1 mb-1"
        onClick={selectAll}
      >
        Select all
      </button>
      <button
        type="button"
        className="btn btn-secondary btn-sm mb-1"
        onClick={deselectAll}
      >
        Deselect all
      </button>
      <br />
      <input
        type="submit"
        value="Run tar2bids with selected files"
        className="btn btn-primary"
        disabled={!mutable}
      />
    </form>
  );
}

TableLauncher.propTypes = {
  rowInfo: PropTypes.arrayOf(PropTypes.object),
  cfmm2tarUrl: PropTypes.string,
  mutable: PropTypes.bool,
};

export default TableLauncher;
