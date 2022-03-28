import React, { useState } from "react";
import PropTypes from "prop-types";

import TableLauncherRow from "./TableLauncherRow";

function TableLauncher(props) {
  const { children, cfmm2tarUrl } = props;
  const [activeIds, setActiveIds] = useState([]);
  return (
    <form method="POST" action={cfmm2tarUrl}>
      <div className="table-responsive" style="max-height: 400px;">
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
            {children.map((child) => (
              <TableLauncherRow
                id={child.id}
                key={child.Id}
                fileName={child.fileName}
                date={child.date}
                isActive={activeIds.includes(child.id)}
                deleteUrl={child.deleteUrl}
                updateActive={setActiveIds}
              />
            ))}
          </tbody>
        </table>
      </div>
    </form>
  );
}

TableLauncher.propTypes = {
  children: PropTypes.arrayOf(PropTypes.element),
  cfmm2tarUrl: PropTypes.string,
};

export default TableLauncher;
